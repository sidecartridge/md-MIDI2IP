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

EPIC-13 STORY-03: an optional **WebSocket** listener (--ws / --ws-port) that
  shares the same ring. TCP and WebSocket players relay to each other through a
  transport-agnostic connection layer (D-13); the byte stream is unchanged.

Usage:  python3 orchestrator/orchestrator.py [--host H] [--port P] [--ws]
"""
from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import logging
import signal
import socket
from dataclasses import dataclass
from itertools import count

import ws  # local: the stdlib RFC 6455 codec (EPIC-13 STORY-02)

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
# Reverse-DNS (PTR) of a connected node's IP — best-effort, off the relay path,
# bounded by this timeout so a slow/missing resolver never stalls a connection.
DNS_TIMEOUT_S = 1.0
_dns_cache: "dict[str, str]" = {}  # ip -> resolved hostname (or the ip on failure)
_bg_tasks: "set" = set()  # keep background lookups referenced so they aren't GC'd


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


class Conn:
    """Transport-agnostic connection wrapper (EPIC-13 STORY-03).

    The relay reads a player's OUT bytes with `recv()` and pushes its IN bytes with
    `send()` + `drain()`, never touching the underlying stream, so a TCP player and a
    WebSocket player run through the same code (D-13). `transport` labels the carrier
    for telemetry."""

    transport = "tcp"

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self.socket = writer.get_extra_info("socket")
        self.peername = writer.get_extra_info("peername")

    @property
    def peer(self) -> str:
        return f"{self.peername[0]}:{self.peername[1]}" if self.peername else "?"

    @property
    def ip(self) -> str:
        return self.peername[0] if self.peername else "?"

    def tune(self) -> None:
        """Apply the socket tuning: TCP_NODELAY, keepalive, a bounded write buffer
        (STORY-04). Both carriers ride a TCP socket, so this is shared."""
        if self.socket is not None:
            try:
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass  # not a TCP socket / unsupported — non-fatal
            _enable_keepalive(self.socket)
        try:
            self._writer.transport.set_write_buffer_limits(high=WRITE_BUFFER_HIGH)
        except (AttributeError, NotImplementedError):
            pass

    async def drain(self) -> None:
        await self._writer.drain()

    def close(self) -> None:
        self._writer.close()

    async def recv(self) -> bytes:  # pragma: no cover - overridden
        raise NotImplementedError

    def send(self, data: bytes) -> None:  # pragma: no cover - overridden
        raise NotImplementedError


class TcpConn(Conn):
    """Raw TCP carrier (D-03): the bytes are the stream, verbatim."""

    transport = "tcp"

    async def recv(self) -> bytes:
        return await self._reader.read(4096)

    def send(self, data: bytes) -> None:
        self._writer.write(data)


class WsConn(Conn):
    """WebSocket carrier (D-13): MIDI bytes ride in binary frames. `recv()` decodes
    frames and answers control frames inline (pong on ping, EOF on close); `send()`
    wraps the bytes in one unmasked binary frame."""

    transport = "ws"

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        super().__init__(reader, writer)
        self._dec = ws.FrameDecoder()

    async def recv(self) -> bytes:
        while True:
            raw = await self._reader.read(4096)
            if not raw:
                return b""  # TCP EOF
            out = bytearray()
            for opcode, payload in self._dec.feed(raw):
                if opcode in (ws.OP_BINARY, ws.OP_CONT, ws.OP_TEXT):
                    out.extend(payload)
                elif opcode == ws.OP_PING:
                    self._writer.write(ws.pong_frame(payload))
                elif opcode == ws.OP_CLOSE:
                    return b""  # peer asked to close
                # OP_PONG: ignore
            if out:
                return bytes(out)
            # only control frames this read: keep reading for data

    def send(self, data: bytes) -> None:
        self._writer.write(ws.binary_frame(data))


@dataclass
class Player:
    """One connected player (a ST+RP, or a Hatari gateway)."""

    id: int
    peer: str  # "ip:port"
    ip: str  # peer host only — node identity for one-connection-per-IP dedup
    conn: "Conn"  # transport-agnostic carrier (EPIC-13); push this player's IN via conn.send
    connected_at: float  # event-loop clock (seconds); for uptime
    bytes_out: int = 0  # bytes received FROM the player (their MIDI OUT)
    bytes_in: int = 0  # bytes sent TO the player (their MIDI IN)
    last_active: float = 0.0  # event-loop time of the last byte received (liveness)
    host: str = ""  # reverse-DNS name (STORY-03); falls back to the IP
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
        player.conn.close()
    except (ConnectionError, OSError):
        pass


def _is_stalled(player: Player, now: float) -> bool:
    """A connected player that has relayed no OUT bytes for RECONNECT_STALE_S — a
    likely dead/half-open node. Used to supersede it when its IP reconnects."""
    return (now - player.last_active) > RECONNECT_STALE_S


async def _resolve_host(player: Player) -> None:
    """Best-effort reverse-DNS (PTR) of the player's IP into player.host. Runs off
    the relay path and is bounded by DNS_TIMEOUT_S, so a slow or missing resolver
    never stalls a connection or the event loop. Cached per IP; on any failure the
    host stays the IP string (the common case — most LAN/home IPs have no PTR)."""
    ip = player.ip
    cached = _dns_cache.get(ip)
    if cached is not None:
        player.host = cached
        return
    host = ip
    try:
        loop = asyncio.get_event_loop()
        name, _ = await asyncio.wait_for(
            loop.getnameinfo((ip, 0), socket.NI_NAMEREQD), timeout=DNS_TIMEOUT_S
        )
        if name and name != ip:
            host = name
    except (asyncio.TimeoutError, socket.gaierror, OSError, ValueError):
        pass  # no PTR record / timeout / unusable sockaddr — keep the IP
    _dns_cache[ip] = host
    player.host = host


async def handle_conn(conn: "Conn") -> None:
    """Per-connection relay, transport-agnostic (EPIC-13 STORY-03): register, relay
    this player's OUT to the next player's IN until EOF, deregister. Hardened
    (STORY-04): keepalive, bounded write buffer, slow-player drop, defensive error
    handling. The body is identical for a TCP or a WebSocket carrier (D-13)."""
    conn.tune()
    peer = conn.peer
    ip = conn.ip

    # Supersede a prior connection from this IP on (re)connect (EPIC-11 STORY-02).
    # A private LAN address is always one-per-IP (a LAN node = one IP). For ANY IP
    # class (incl. loopback / NAT, which are exempt from the strict dedup), a
    # *stalled* prior connection is a dead node that never FIN'd; drop it so the
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
        conn=conn,
        connected_at=now,
        last_active=now,
    )
    registry.add(player)
    player.host = ip  # until the reverse-DNS lookup resolves it
    task = asyncio.ensure_future(_resolve_host(player))  # best-effort PTR, off the relay
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    if _inspect:
        player.inspector = MidiMazeInspector()
    LOG.info("player %d connected from %s via %s (%d online)",
             player.id, peer, conn.transport, len(registry))

    try:
        while True:
            data = await conn.recv()
            if not data:
                break  # clean EOF (TCP close or WebSocket close frame)
            player.bytes_out += len(data)
            player.last_active = asyncio.get_event_loop().time()
            # Forward this player's OUT bytes to the next player's IN, verbatim
            # (D-02): a dumb relay; the firmware owns the ring (EPIC-09). Single
            # source per target, so no interleaving.
            target = registry.next_player(player)
            if player.inspector is not None:  # --inspect: read-only protocol decode
                LOG.info("inspect p%d(%s) -> p%s: %s | %s", player.id, peer,
                         target.id if target else "-", data.hex(" "),
                         " ".join(player.inspector.feed(data)))
            if target is None:
                continue  # no ring peer yet (lone node)
            try:
                target.conn.send(data)
                # Bound the wait so one stuck player can't freeze the ring.
                await asyncio.wait_for(
                    target.conn.drain(), timeout=SLOW_PLAYER_TIMEOUT_S
                )
                target.bytes_in += len(data)
            except asyncio.TimeoutError:
                _drop_player(target, "too slow (write backpressure)")
            except (ConnectionError, OSError):
                # Do NOT drop the target here. A relay write can hit a transient
                # error, and dropping mid-game collapses a 2-node ring to a
                # ring-of-one that echoes a node's OUT back into its own IN, which
                # MIDI Maze re-sends in a tight loop (a flood) while the dropped
                # node reconnect-thrashes. The target's own handler (EOF/finally)
                # and TCP keepalive deregister a genuinely dead peer.
                pass
    except (ConnectionError, OSError) as exc:
        LOG.info("player %d (%s) read error: %s", player.id, peer, exc)
    except Exception:  # one bad connection must never take down the server
        LOG.exception("player %d (%s) handler crashed", player.id, peer)
    finally:
        registry.remove(player.id)
        conn.close()  # don't await wait_closed(): can hang under shutdown-cancel
        LOG.info(
            "player %d (%s) disconnected; %d bytes out / %d in (%d online)",
            player.id,
            peer,
            player.bytes_out,
            player.bytes_in,
            len(registry),
        )


async def handle_player(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """TCP entry point (asyncio.start_server): relay over a raw-TCP carrier."""
    await handle_conn(TcpConn(reader, writer))


async def handle_ws(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """WebSocket entry point (EPIC-13 STORY-03): run the RFC 6455 server handshake,
    then relay over a WebSocket carrier in the same ring as the TCP players."""
    try:
        request_line = await reader.readline()
        if not request_line:
            writer.close()
            return
        raw_headers = bytearray()
        while True:  # read header lines up to the blank line
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            raw_headers += line
        headers = ws.parse_headers(bytes(raw_headers))
        key = headers.get("sec-websocket-key", "")
        if not key or not ws.is_upgrade(headers):
            writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        writer.write(ws.handshake_response(key))
        await writer.drain()
    except (ConnectionError, OSError):
        writer.close()
        return
    await handle_conn(WsConn(reader, writer))


# --- STORY-03: HTTP status -------------------------------------------------
# Served inside the same asyncio loop as the relay, so reading `registry` is
# race-free (single-threaded) — no http.server thread, no locks. Read-only.


def _status_snapshot() -> dict:
    """Race-free status snapshot, read from the asyncio loop. Schema (status.json):

      uptime_s, listen, players_online   server-level fields
      ring        [player id, ...] in ring order — the relay forwards each node's
                  OUT to the *next* id, wrapping (a lone node echoes to itself)
      players     [ {id, ip, host, peer, transport, connected_s, idle_s, bytes_out,
                    bytes_in}, ... ] in ring order. transport = tcp | ws (the node's
                  carrier, D-13). bytes_out = received FROM the node (its
                  MIDI OUT); bytes_in = sent TO the node (its MIDI IN); idle_s =
                  seconds since the node's last byte (UI can dim a stalled node).

    The HTML ring view (STORY-05) and any external tooling rely on this shape."""
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
                "ip": p.ip,
                "host": p.host,
                "peer": p.peer,
                "transport": p.conn.transport,
                "connected_s": int(now - p.connected_at),
                "idle_s": int(now - p.last_active),
                "bytes_out": p.bytes_out,
                "bytes_in": p.bytes_in,
            }
            for p in players
        ],
    }


def _status_json() -> bytes:
    return json.dumps(_status_snapshot(), indent=2).encode("utf-8")


# Self-contained ring-visualization page (STORY-05): no external/CDN deps. It
# polls /status.json every 2 s and (re)draws the ring in SVG — nodes around a
# circle in relay order with arrowheads for the forward direction, each labelled
# with host/IP and bytes out/in; a node idle past STALE seconds is dimmed; an
# unreachable status.json degrades to a banner. Served verbatim (the JS holds the
# live data), so the page itself never needs server-side templating.
_STATUS_PAGE = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>MIDI-to-IP orchestrator</title><style>"
    "body{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"
    "background:#0e1116;color:#d8dee9}"
    "header{padding:.7em 1.1em;border-bottom:1px solid #21262d}"
    "h1{font-size:1.05em;margin:0}"
    "#meta{color:#8b949e;font-size:.85em;margin-top:.3em}"
    "svg{display:block;width:100%;height:82vh}"
    ".node circle{fill:#161b22;stroke:#4f9cff;stroke-width:2}"
    ".node.stalled circle{stroke:#5a6068}"
    ".node text{fill:#d8dee9;font-size:13px;text-anchor:middle}"
    ".node .sub{fill:#8b949e;font-size:11px}"
    ".node.stalled text{fill:#6b7280}"
    ".edge{stroke:#3a4250;stroke-width:1.5;fill:none;marker-end:url(#a)}"
    ".empty{fill:#8b949e;font-size:15px;text-anchor:middle}"
    "</style></head><body>"
    "<header><h1>MIDI-to-IP orchestrator</h1>"
    "<div id='meta'>connecting...</div></header>"
    "<svg viewBox='0 0 800 600' preserveAspectRatio='xMidYMid meet'>"
    "<defs><marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' "
    "markerHeight='7' orient='auto-start-reverse'>"
    "<path d='M0 0L10 5L0 10z' fill='#3a4250'/></marker></defs>"
    "<g id='edges'></g><g id='nodes'></g></svg>"
    "<script>"
    "const NS='http://www.w3.org/2000/svg',STALE=10,CX=400,CY=300,R=205;"
    "function el(t,a,p){const e=document.createElementNS(NS,t);"
    "for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}"
    "function pos(i,n){if(n===1)return[CX,CY];"
    "const g=(i/n)*2*Math.PI-Math.PI/2;return[CX+R*Math.cos(g),CY+R*Math.sin(g)]}"
    "async function tick(){let s;"
    "try{s=await(await fetch('status.json',{cache:'no-store'})).json()}"
    "catch(e){document.getElementById('meta').textContent="
    "'orchestrator unreachable (retrying)';return}"
    "document.getElementById('meta').textContent='uptime '+s.uptime_s+'s | game '"
    "+s.listen+' | '+s.players_online+' online';"
    "const E=document.getElementById('edges'),N=document.getElementById('nodes');"
    "E.textContent='';N.textContent='';"
    "const ps=s.players||[],n=ps.length;"
    "if(!n){el('text',{x:CX,y:CY,class:'empty'},N).textContent="
    "'(no nodes connected)';return}"
    "const P=ps.map((p,i)=>pos(i,n));"
    # edges: data flows OUT of a node into the next node's IN, drawn as an arc
    # along the ring (arrowhead = direction). n=1 echoes to itself (a self-loop).
    "if(n===1){el('path',{class:'edge',d:'M '+(CX+38)+' '+(CY-14)+' C '+(CX+86)"
    "+' '+(CY-86)+' '+(CX-86)+' '+(CY-86)+' '+(CX-38)+' '+(CY-14)},E)}"
    "else{const G=36/R+0.05;for(let i=0;i<n;i++){"
    "const a1=(i/n)*2*Math.PI-Math.PI/2+G,a2=((i+1)/n)*2*Math.PI-Math.PI/2-G;"
    "const x1=CX+R*Math.cos(a1),y1=CY+R*Math.sin(a1),"
    "x2=CX+R*Math.cos(a2),y2=CY+R*Math.sin(a2);"
    "el('path',{class:'edge',d:'M '+x1+' '+y1+' A '+R+' '+R+' 0 0 1 '+x2+' '+y2},E)}}"
    "ps.forEach((p,i)=>{const X=P[i][0],Y=P[i][1];"
    "const gg=el('g',{class:'node'+(p.idle_s>STALE?' stalled':'')},N);"
    "el('circle',{cx:X,cy:Y,r:36},gg);"
    "el('text',{x:X,y:Y-6},gg).textContent='#'+p.id;"
    "el('text',{x:X,y:Y+11,class:'sub'},gg).textContent="
    "(p.host||p.ip)+' ['+(p.transport||'tcp')+']';"
    "el('text',{x:X,y:Y+54,class:'sub'},gg).textContent="
    "'out '+p.bytes_out+'  in '+p.bytes_in})}"
    "tick();setInterval(tick,2000);"
    "</script></body></html>"
).encode("utf-8")


def _status_html() -> bytes:
    return _STATUS_PAGE


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


async def serve(host: str, port: int, http_port: int, enable_http: bool = True,
                ws_enabled: bool = False, ws_port: int = 5006) -> None:
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
    wssrv = None
    if ws_enabled:
        # Optional WebSocket players (D-13), in the same ring as the TCP players.
        wssrv = await asyncio.start_server(handle_ws, host, ws_port)
    LOG.info(
        "orchestrator: game(tcp) on %s:%d%s%s",
        host, port,
        f", ws on {host}:{ws_port}" if ws_enabled else "",
        f", HTTP status on {host}:{http_port}" if enable_http else " (HTTP status disabled)",
    )
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
                player.conn.close()
            except (ConnectionError, OSError):
                pass
        game.close()
        if http is not None:
            http.close()
        if wssrv is not None:
            wssrv.close()


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
    parser.add_argument(
        "--ws", action="store_true",
        help="also accept WebSocket players on --ws-port (RFC 6455, D-13); off by "
             "default, so the TCP-only behaviour is unchanged. A WebSocket node and "
             "a TCP node share one ring.",
    )
    parser.add_argument(
        "--ws-port", type=int, default=5006,
        help="WebSocket port when --ws is set (default: 5006)",
    )
    args = parser.parse_args()
    global _inspect
    _inspect = args.inspect
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        asyncio.run(serve(args.host, args.port, args.http_port,
                          enable_http=not args.no_http,
                          ws_enabled=args.ws, ws_port=args.ws_port))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()
