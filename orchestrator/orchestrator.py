#!/usr/bin/env python3
"""MIDI-to-IP orchestrator — EPIC-04.

A central server that connects players into a MIDI Maze ring by relaying raw
bytes (D-02/D-04). Python 3 **standard library only** — no third-party packages,
ever.

Scope so far:
  - STORY-01: asyncio TCP server; a registry of players (id, peer, connect time,
    byte counters).
  - STORY-02: the **ring relay** — each player's OUT bytes are forwarded to the
    next player's IN (insertion order, wrapping). A lone node has no peer and
    gets nothing back (no self-echo), so it can't elect/count before the ring
    forms (D-04).
  - STORY-03: a read-only **HTTP status** interface on a separate port (HTML page
    + `/status.json`), served in the same asyncio loop (race-free registry reads).
  - STORY-04: **robustness** — TCP keepalive (dead-player detection), bounded
    write buffers, slow-player drop (a stuck node can't freeze the ring),
    one-connection-per-**private**-IP (a reconnect supersedes a node's stale
    half-open connection; public/NAT gateways and loopback are exempt),
    defensive per-connection error handling, and clean Ctrl-C shutdown.

Usage:  python3 orchestrator/orchestrator.py [--host H] [--port P]
"""
from __future__ import annotations

import argparse
import asyncio
import html
import ipaddress
import json
import logging
import signal
import socket
from dataclasses import dataclass
from itertools import count

LOG = logging.getLogger("orchestrator")

_next_id = count(1)  # monotonic player ids
_started_at = 0.0  # event-loop clock when serving began (for uptime)
_listen_addr = ""  # "host:port" of the game TCP server, for display
_inspect = False  # --inspect: decode the MIDI Maze protocol as traffic passes


# --- MIDI Maze protocol inspection (in-line, read-only) --------------------
# When --inspect is on, each player's MIDI-OUT stream is decoded into protocol
# events as it is relayed, so the log shows COUNT-PLAYERS / START-GAME / JOYSTICK
# etc. instead of raw hex. From Markus Fritze's protocol (thesis 2.4.2 / Anexo A):
# a SLAVE re-sends every message it receives; the MASTER expects its message back.
_MM_MASTER_ELECT = 0x00
_MM_COUNT_PLAYERS = 0x80  # 0x80 <n>: master sends 0x80 0x00; each slave inc's <n>
_MM_RESET_SCORE = 0x81
_MM_TERMINATE_GAME = 0x82
_MM_SEND_DATA = 0x83  # name\0 + maze-size + speeds + lives + 3 drones + 4096 maze + …
_MM_START_GAME = 0x84
_MM_ABOUT = 0x85
_MM_NAME_DIALOG = 0x86
# SEND-DATA fixed tail after the 0-terminated name: maze-size(1)+recharge(1)+
# regen(1)+reappear(1)+lives(1)+drones(3)+maze(4096)+teams-flag(1)+teams(16)+
# friendly-fire(1)+seed(2).
_MM_SEND_DATA_FIXED = 1 + 1 + 1 + 1 + 1 + 3 + 4096 + 1 + 16 + 1 + 2  # 4123


def _mm_joystick(b: int) -> str:
    names = [n for n, m in (("L", 1), ("R", 2), ("D", 4), ("U", 8), ("Fire", 16)) if b & m]
    return "+".join(names) if names else "none"


class MidiMazeInspector:
    """Stateful per-player decoder: feed() OUT bytes, get protocol-event labels.
    Best-effort (not fully phase-aware) — enough to read the setup handshake
    where master election and COUNT-PLAYERS live."""

    def __init__(self) -> None:
        self._state = "normal"
        self._fixed_left = 0
        self._in_game = False

    def feed(self, data: bytes) -> "list[str]":
        events: "list[str]" = []
        for b in data:
            events.extend(self._byte(b))
        return events

    def _byte(self, b: int) -> "list[str]":
        if self._state == "expect_count":  # the byte after 0x80 is the count
            self._state = "normal"
            return [f"COUNT-PLAYERS(n={b})"]
        if self._state == "send_data_name":  # consume the 0-terminated name
            if b == 0x00:
                self._state = "send_data_fixed"
                self._fixed_left = _MM_SEND_DATA_FIXED
            return []
        if self._state == "send_data_fixed":  # consume the fixed game-data tail
            self._fixed_left -= 1
            if self._fixed_left <= 0:
                self._state = "normal"
                self._in_game = True
                return ["SEND-DATA(end)"]
            return []
        if b == _MM_COUNT_PLAYERS:
            self._state = "expect_count"
            return ["COUNT-PLAYERS-start"]  # designate master NOW, not after the count byte
        if b == _MM_RESET_SCORE:
            return ["RESET-SCORE"]
        if b == _MM_TERMINATE_GAME:
            return ["TERMINATE-GAME"]
        if b == _MM_SEND_DATA:
            self._state = "send_data_name"
            return ["SEND-DATA(start)"]
        if b == _MM_START_GAME:
            return ["START-GAME"]
        if b == _MM_ABOUT:
            return ["ABOUT"]
        if b == _MM_NAME_DIALOG:
            return ["NAME-DIALOG"]
        if b == _MM_MASTER_ELECT:
            return [f"JOYSTICK({_mm_joystick(b)})"] if self._in_game else ["MASTER-ELECT"]
        return [f"JOYSTICK({_mm_joystick(b)})"] if self._in_game else [f"byte(0x{b:02x})"]


def _should_dedup_ip(ip: str) -> bool:
    """Whether one-connection-per-IP applies to this peer.

    Only **private-network** addresses (RFC 1918 / link-local) — a LAN node = one
    IP, so a reconnect must supersede its stale connection. NOT public addresses
    (a NAT gateway legitimately hides many players behind one IP) and NOT loopback
    (so local multi-client testing / two emulators on one host can coexist)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private and not addr.is_loopback

# A player whose IN can't be written for this long (TCP backpressure) is treated
# as stuck and dropped, so one slow node can't freeze the lock-step ring.
SLOW_PLAYER_TIMEOUT_S = 5.0
WRITE_BUFFER_HIGH = 64 * 1024  # bound per-connection write buffer (bytes)
# A prior connection from a reconnecting IP that has relayed nothing for this long
# is treated as a stalled/dead node (it never FIN'd) and superseded by the
# reconnection — even for IP classes exempt from the strict one-per-IP dedup
# (loopback/NAT). The reconnection always gets a fresh, incremented node id.
RECONNECT_STALE_S = 10.0


def _enable_keepalive(sock: socket.socket) -> None:
    """Detect a silently-dead player (no FIN) in ~10s instead of TCP's default.
    Same approach as tools/echo_peer.py."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "TCP_KEEPIDLE"):  # Linux
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        elif hasattr(socket, "TCP_KEEPALIVE"):  # macOS
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 5)
    except OSError:
        pass  # unsupported — non-fatal


@dataclass
class Player:
    """One connected player (a ST+RP, or a Hatari gateway)."""

    id: int
    peer: str  # "ip:port"
    ip: str  # peer host only — node identity for one-connection-per-IP dedup
    writer: asyncio.StreamWriter  # used by STORY-02 to push this player's IN bytes
    connected_at: float  # event-loop clock (seconds); for uptime
    bytes_out: int = 0  # bytes received FROM the player (their MIDI OUT)
    bytes_in: int = 0  # bytes sent TO the player (their MIDI IN)
    last_active: float = 0.0  # event-loop time of the last byte received (liveness)
    inspector: "MidiMazeInspector | None" = None  # per-player --inspect decoder


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
        """The player after `player` in the ring (insertion order, wrapping), or
        None if `player` is gone. A **ring of one echoes to self** — a lone peer's
        OUT comes back to its own IN, so it can read its `0x00` back and become
        MASTER (the EPIC-01 loopback case). Computed fresh each call (the ring
        re-forms on every join/leave)."""
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


def _drop_player(player: Player, reason: str) -> None:
    """Remove a player from the ring and close its socket (STORY-04). Its own
    handler coroutine then finishes via EOF and logs the disconnect. Idempotent."""
    registry.remove(player.id)
    LOG.warning("dropping player %d (%s): %s", player.id, player.peer, reason)
    try:
        player.writer.close()
    except (ConnectionError, OSError):
        pass


def _is_stalled(player: Player, now: float) -> bool:
    """A connected player that has relayed no OUT bytes for RECONNECT_STALE_S — a
    likely dead/half-open node. Used to supersede it when its IP reconnects."""
    return (now - player.last_active) > RECONNECT_STALE_S


async def handle_player(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Per-connection coroutine: register, relay this player's OUT to the next
    player's IN until EOF, deregister. Hardened (STORY-04): keepalive, bounded
    write buffer, slow-player drop, and defensive error handling."""
    sock = writer.get_extra_info("socket")
    if sock is not None:
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass  # not a TCP socket / unsupported — non-fatal
        _enable_keepalive(sock)
    try:
        writer.transport.set_write_buffer_limits(high=WRITE_BUFFER_HIGH)
    except (AttributeError, NotImplementedError):
        pass

    peername = writer.get_extra_info("peername")
    peer = f"{peername[0]}:{peername[1]}" if peername else "?"
    ip = peername[0] if peername else "?"

    # Supersede a prior connection from this IP on (re)connect (EPIC-11 STORY-02).
    # A private LAN address is always one-per-IP (a LAN node = one IP). For ANY IP
    # class (incl. loopback / NAT, which are exempt from the strict dedup), a
    # *stalled* prior connection is a dead node that never FIN'd — drop it so the
    # reconnection doesn't leave a phantom. The reconnection always gets a fresh,
    # incremented node id.
    now = asyncio.get_event_loop().time()
    for existing in registry.players():
        if existing.ip != ip:
            continue
        if _should_dedup_ip(ip):
            _drop_player(existing, f"superseded (LAN one-per-IP) by reconnection from {ip}")
        elif _is_stalled(existing, now):
            _drop_player(existing, f"superseded (prior connection stalled) by reconnection from {ip}")

    player = Player(
        id=next(_next_id),
        peer=peer,
        ip=ip,
        writer=writer,
        connected_at=now,
        last_active=now,
    )
    registry.add(player)
    if _inspect:
        player.inspector = MidiMazeInspector()
    LOG.info("player %d connected from %s (%d online)", player.id, peer, len(registry))

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break  # clean EOF (peer closed)
            player.bytes_out += len(data)
            player.last_active = asyncio.get_event_loop().time()
            # Forward this player's OUT bytes to the next player's IN, verbatim
            # (D-02) — a dumb relay; the firmware owns the ring (EPIC-09). Single
            # source per target, so no interleaving.
            target = registry.next_player(player)
            if player.inspector is not None:  # --inspect: read-only protocol decode
                LOG.info("inspect p%d(%s) -> p%s: %s | %s", player.id, peer,
                         target.id if target else "-", data.hex(" "),
                         " ".join(player.inspector.feed(data)))
            if target is None:
                continue  # no ring peer yet (lone node)
            try:
                target.writer.write(data)
                # Bound the wait so one stuck player can't freeze the ring.
                await asyncio.wait_for(
                    target.writer.drain(), timeout=SLOW_PLAYER_TIMEOUT_S
                )
                target.bytes_in += len(data)
            except asyncio.TimeoutError:
                _drop_player(target, "too slow (write backpressure)")
            except (ConnectionError, OSError):
                pass  # target died; its own handler will deregister it
    except (ConnectionError, OSError) as exc:
        LOG.info("player %d (%s) read error: %s", player.id, peer, exc)
    except Exception:  # one bad connection must never take down the server
        LOG.exception("player %d (%s) handler crashed", player.id, peer)
    finally:
        registry.remove(player.id)
        writer.close()  # don't await wait_closed(): can hang under shutdown-cancel
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


async def serve(host: str, port: int, http_port: int, enable_http: bool = True) -> None:
    global _started_at, _listen_addr
    loop = asyncio.get_event_loop()
    _started_at = loop.time()
    _listen_addr = f"{host}:{port}"

    # Clean shutdown via signals (asyncio-idiomatic; KeyboardInterrupt in main()
    # is the fallback where add_signal_handler isn't supported, e.g. Windows).
    stop = loop.create_future()

    def _request_stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except (NotImplementedError, RuntimeError):
            pass

    game = await asyncio.start_server(handle_player, host, port)
    http = None
    if enable_http:
        # HTTP status shares this event loop with the game relay. --no-http drops
        # it so a status poll can never add jitter to the lock-step ring (C-01).
        http = await asyncio.start_server(handle_http, host, http_port)
        LOG.info("orchestrator: game on %s:%d, HTTP status on %s:%d",
                 host, port, host, http_port)
    else:
        LOG.info("orchestrator: game on %s:%d (HTTP status disabled)", host, port)
    try:
        # start_server is already accepting; stay alive until asked to stop.
        await stop
    finally:
        # Close active player connections FIRST (unblocks their idle reader.read),
        # then the listeners. We deliberately do NOT use `async with` /
        # `await server.wait_closed()`: on Python 3.13+ that blocks until every
        # active connection closes, which hangs shutdown while a player (the RP)
        # sits idle in reader.read().
        LOG.info("shutting down; closing %d player connection(s)", len(registry))
        for player in registry.players():
            try:
                player.writer.close()
            except (ConnectionError, OSError):
                pass
        game.close()
        if http is not None:
            http.close()


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
    parser.add_argument(
        "--no-http", action="store_true",
        help="disable the HTTP status server (rules out status-poll jitter on the "
             "game relay; C-01)",
    )
    parser.add_argument(
        "--inspect", action="store_true",
        help="decode + log the MIDI Maze protocol as traffic passes (read-only)",
    )
    args = parser.parse_args()
    global _inspect
    _inspect = args.inspect
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        asyncio.run(serve(args.host, args.port, args.http_port,
                          enable_http=not args.no_http))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()
