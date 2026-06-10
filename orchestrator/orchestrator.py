#!/usr/bin/env python3
"""MIDI-to-IP orchestrator — EPIC-04.

A central server that connects players into a MIDI Maze ring by relaying raw
bytes (D-02/D-04). Python 3 **standard library only** — no third-party packages,
ever.

Scope so far:
  - STORY-01: asyncio TCP server; a registry of players (id, peer, connect time,
    byte counters).
  - STORY-02: the **ring relay** — each player's OUT bytes are forwarded to the
    next player's IN (insertion order, wrapping; a ring of one echoes to self).
  - STORY-03: a read-only **HTTP status** interface on a separate port (HTML page
    + `/status.json`), served in the same asyncio loop (race-free registry reads).

Usage:  python3 orchestrator/orchestrator.py [--host H] [--port P]
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import logging
import socket
from dataclasses import dataclass
from itertools import count

LOG = logging.getLogger("orchestrator")

_next_id = count(1)  # monotonic player ids
_started_at = 0.0  # event-loop clock when serving began (for uptime)
_listen_addr = ""  # "host:port" of the game TCP server, for display


@dataclass
class Player:
    """One connected player (a ST+RP, or a Hatari gateway)."""

    id: int
    peer: str  # "ip:port"
    writer: asyncio.StreamWriter  # used by STORY-02 to push this player's IN bytes
    connected_at: float  # event-loop clock (seconds); for uptime
    bytes_out: int = 0  # bytes received FROM the player (their MIDI OUT)
    bytes_in: int = 0  # bytes sent TO the player (their MIDI IN)


class Registry:
    """Ordered set of connected players. Insertion order defines the ring order
    that STORY-02 will relay around; STORY-03 reads it for HTTP status."""

    def __init__(self) -> None:
        self._players: "dict[int, Player]" = {}

    def add(self, player: Player) -> None:
        self._players[player.id] = player

    def remove(self, player_id: int) -> None:
        self._players.pop(player_id, None)

    def players(self) -> "list[Player]":
        return list(self._players.values())

    def next_player(self, player: Player) -> "Player | None":
        """The player after `player` in the ring (insertion order, wrapping).

        Ring of one -> the player itself (self-loop / echo, the faithful
        ring-of-one). Returns None if `player` is no longer connected. Computed
        fresh each call so the ring re-forms on every join/leave."""
        ids = list(self._players)
        if player.id not in self._players:
            return None
        if len(ids) == 1:
            return player  # ring of one: echo back to self
        nxt = ids[(ids.index(player.id) + 1) % len(ids)]
        return self._players[nxt]

    def __len__(self) -> int:
        return len(self._players)


# Single shared registry (STORY-02 ring relay + STORY-03 HTTP read from this).
registry = Registry()


async def handle_player(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Per-connection coroutine: register, read (count) until EOF, deregister."""
    sock = writer.get_extra_info("socket")
    if sock is not None:
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass  # not a TCP socket / unsupported — non-fatal

    peername = writer.get_extra_info("peername")
    peer = f"{peername[0]}:{peername[1]}" if peername else "?"
    player = Player(
        id=next(_next_id),
        peer=peer,
        writer=writer,
        connected_at=asyncio.get_event_loop().time(),
    )
    registry.add(player)
    LOG.info("player %d connected from %s (%d online)", player.id, peer, len(registry))

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break  # clean EOF (peer closed)
            player.bytes_out += len(data)
            # STORY-02: forward this player's OUT bytes to the next player's IN,
            # verbatim (D-02). Single source per target (the ring's predecessor),
            # so no interleaving. A ring of one echoes back to self.
            target = registry.next_player(player)
            if target is not None:
                try:
                    target.writer.write(data)
                    await target.writer.drain()
                    target.bytes_in += len(data)
                except (ConnectionError, OSError):
                    pass  # target died; its own handler will deregister it
    except (ConnectionError, OSError) as exc:
        LOG.info("player %d (%s) read error: %s", player.id, peer, exc)
    finally:
        registry.remove(player.id)
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass
        LOG.info(
            "player %d (%s) disconnected; %d bytes out / %d in (%d online)",
            player.id,
            peer,
            player.bytes_out,
            player.bytes_in,
            len(registry),
        )


# --- STORY-03: HTTP status -------------------------------------------------
# Served inside the same asyncio loop as the relay, so reading `registry` is
# race-free (single-threaded) — no http.server thread, no locks. Read-only.


def _status_snapshot() -> dict:
    now = asyncio.get_event_loop().time()
    players = registry.players()
    return {
        "uptime_s": int(now - _started_at),
        "listen": _listen_addr,
        "players_online": len(players),
        "ring": [p.id for p in players],  # ring order = insertion order, wraps
        "players": [
            {
                "id": p.id,
                "peer": p.peer,
                "connected_s": int(now - p.connected_at),
                "bytes_out": p.bytes_out,
                "bytes_in": p.bytes_in,
            }
            for p in players
        ],
    }


def _status_json() -> bytes:
    return json.dumps(_status_snapshot(), indent=2).encode("utf-8")


def _status_html() -> bytes:
    s = _status_snapshot()
    ring = s["ring"]
    if not ring:
        ring_str = "(empty)"
    elif len(ring) == 1:
        ring_str = f"{ring[0]} → {ring[0]} (self)"
    else:
        ring_str = " → ".join(str(i) for i in ring) + f" → {ring[0]}"
    rows = "".join(
        "<tr><td>{id}</td><td>{peer}</td><td>{connected_s}s</td>"
        "<td>{bytes_out}</td><td>{bytes_in}</td></tr>".format(
            id=p["id"],
            peer=html.escape(p["peer"]),
            connected_s=p["connected_s"],
            bytes_out=p["bytes_out"],
            bytes_in=p["bytes_in"],
        )
        for p in s["players"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>MIDI-to-IP orchestrator</title>"
        "<meta http-equiv='refresh' content='2'>"
        "<style>body{{font-family:monospace;margin:2em}}"
        "table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:.3em .7em;text-align:left}}"
        "</style></head><body>"
        "<h1>MIDI-to-IP orchestrator</h1>"
        "<p>uptime {uptime_s}s &middot; game {listen} &middot; players online {players_online}</p>"
        "<p>ring: {ring}</p>"
        "<table><tr><th>id</th><th>peer</th><th>connected</th>"
        "<th>bytes out</th><th>bytes in</th></tr>{rows}</table>"
        "</body></html>"
    ).format(
        uptime_s=s["uptime_s"],
        listen=html.escape(s["listen"]),
        players_online=s["players_online"],
        ring=ring_str,
        rows=rows or "<tr><td colspan='5'>(no players)</td></tr>",
    )
    return page.encode("utf-8")


async def handle_http(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Minimal read-only HTTP/1.1 responder: / -> HTML, /status.json -> JSON."""
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        parts = request_line.decode("latin-1").split()
        path = parts[1] if len(parts) >= 2 else "/"
        while True:  # consume headers up to the blank line
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
        if path.startswith("/status.json"):
            body, ctype = _status_json(), "application/json"
        else:
            body, ctype = _status_html(), "text/html; charset=utf-8"
        writer.write(
            (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {ctype}\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("latin-1")
            + body
        )
        await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def serve(host: str, port: int, http_port: int) -> None:
    global _started_at, _listen_addr
    _started_at = asyncio.get_event_loop().time()
    _listen_addr = f"{host}:{port}"
    game = await asyncio.start_server(handle_player, host, port)
    http = await asyncio.start_server(handle_http, host, http_port)
    LOG.info("orchestrator: game on %s:%d, HTTP status on %s:%d",
             host, port, host, http_port)
    async with game, http:
        await asyncio.gather(game.serve_forever(), http.serve_forever())


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-to-IP orchestrator (EPIC-04)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5005, help="game TCP port (default: 5005)"
    )
    parser.add_argument(
        "--http-port", type=int, default=8080, help="HTTP status port (default: 8080)"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        asyncio.run(serve(args.host, args.port, args.http_port))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()
