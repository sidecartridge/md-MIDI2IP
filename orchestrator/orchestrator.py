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
It does **not** yet serve HTTP status (-> STORY-03); the `registry` is exposed
for that.

Usage:  python3 orchestrator/orchestrator.py [--host H] [--port P]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import socket
from dataclasses import dataclass
from itertools import count

LOG = logging.getLogger("orchestrator")

_next_id = count(1)  # monotonic player ids


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


async def serve(host: str, port: int) -> None:
    server = await asyncio.start_server(handle_player, host, port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    LOG.info("orchestrator listening on %s", addrs)
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-to-IP orchestrator (EPIC-04)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5005, help="game TCP port (default: 5005)"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        asyncio.run(serve(args.host, args.port))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()
