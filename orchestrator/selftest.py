#!/usr/bin/env python3
"""Orchestrator self-test — EPIC-04 STORY-05.

Spawns orchestrator.py on test ports and validates it end to end:
  Phase A (ring): two clients form a 2-ring; A<->B byte-exact; HTTP /status.json
    reflects players + ring; a drop re-forms the ring and a reconnect rejoins.
    (Both clients are on loopback, which is exempt from the per-IP dedup.)
  Phase B (dedup classification): one-connection-per-IP applies to private LAN
    addresses only — not public (NAT may hide many) or loopback (local testing).
  Phase C (--inspect decoder): the read-only MidiMazeInspector decodes a protocol
    byte stream into event labels (the only protocol awareness left after the
    relay went back to dumb — EPIC-11 STORY-01).
  Phase D (websocket codec): the stdlib RFC 6455 handshake + frame codec (ws.py),
    unit-tested in isolation before it is wired into the listener (EPIC-13 STORY-03).

Stdlib only. Exit code 0 = PASS, 1 = FAIL.

Usage:  python3 orchestrator/selftest.py
"""
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # import the local ws codec
import ws  # noqa: E402

HOST = "127.0.0.1"
_failures: "list[str]" = []


def check(name: str, ok: bool) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        _failures.append(name)


def conn(port: int) -> socket.socket:
    s = socket.create_connection((HOST, port))
    s.settimeout(2.0)
    return s


def recv_exact(s: socket.socket, n: int) -> bytes:
    buf = b""
    try:
        while len(buf) < n:
            chunk = s.recv(n - len(buf))
            if not chunk:
                break
            buf += chunk
    except (socket.timeout, OSError):
        pass
    return buf


def try_recv(s: socket.socket, n: int = 16, timeout: float = 0.5) -> bytes:
    """Best-effort recv; returns b'' if nothing arrives within `timeout`."""
    s.settimeout(timeout)
    try:
        return s.recv(n)
    except (socket.timeout, BlockingIOError, OSError):
        return b""


def status(http_port: int) -> dict:
    with urllib.request.urlopen(
        f"http://{HOST}:{http_port}/status.json", timeout=2
    ) as resp:
        return json.loads(resp.read())


@contextmanager
def server(port: int, http_port: int, *extra: str):
    here = Path(__file__).resolve().parent
    proc = subprocess.Popen(
        [
            sys.executable, str(here / "orchestrator.py"),
            "--host", HOST, "--port", str(port), "--http-port", str(http_port),
            *extra,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):  # wait for the listener
            try:
                conn(port).close()
                break
            except OSError:
                time.sleep(0.1)
        time.sleep(0.2)
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def http_req(http_port: int, method: str, path: str, body: "bytes | None" = None,
             headers: "dict | None" = None) -> "tuple[int, bytes]":
    """REST helper: returns (status_code, body). HTTP errors return their code too."""
    req = urllib.request.Request(
        f"http://{HOST}:{http_port}{path}", data=body, method=method
    )
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def ws_connect(port: int, room: str = "") -> "tuple[socket.socket, bool]":
    """Open a TCP socket and run the RFC 6455 client handshake. Returns the socket
    and whether the server answered 101 with the right Sec-WebSocket-Accept. An
    optional room key is sent as Authorization: Bearer (EPIC-14)."""
    s = socket.create_connection((HOST, port))
    s.settimeout(2.0)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    auth = f"Authorization: Bearer {room}\r\n" if room else ""
    s.sendall(
        (
            f"GET / HTTP/1.1\r\nHost: {HOST}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"{auth}Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("latin-1")
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(1024)
        if not chunk:
            break
        buf += chunk
    ok = b" 101 " in buf and ws.accept_key(key).encode("ascii") in buf
    return s, ok


def ws_send(s: socket.socket, data: bytes) -> None:
    """Send data as a masked binary frame (client-to-server frames must be masked)."""
    s.sendall(ws.binary_frame(data, mask_key=os.urandom(4)))


def ws_recv(s: socket.socket, dec: "ws.FrameDecoder", n: int, timeout: float = 2.0) -> bytes:
    """Read until at least n application bytes have been decoded from server frames."""
    s.settimeout(timeout)
    out = bytearray()
    try:
        while len(out) < n:
            chunk = s.recv(4096)
            if not chunk:
                break
            for opcode, payload in dec.feed(chunk):
                if opcode in (ws.OP_BINARY, ws.OP_CONT):
                    out.extend(payload)
    except (socket.timeout, OSError):
        pass
    return bytes(out)


def main() -> int:
    # Phase A — ring relay + status + drop/reconnect. Both clients are on
    # 127.0.0.1 (loopback is exempt from the per-IP dedup, so they coexist).
    with server(5099, 8099):
        print("ring relay (2 players):")
        a, b = conn(5099), conn(5099)
        time.sleep(0.3)
        a.sendall(b"\x00\x80\x01")
        check("A->B byte-exact", recv_exact(b, 3) == b"\x00\x80\x01")
        b.sendall(b"\xaa\xbb")
        check("B->A byte-exact", recv_exact(a, 2) == b"\xaa\xbb")

        print("HTTP status:")
        st = status(8099)
        check("2 players online", st["players_online"] == 2)
        check("ring has 2 entries", len(st["ring"]) == 2)
        check("players have byte counters",
              all("bytes_out" in p and "bytes_in" in p for p in st["players"]))
        check("players have a host field (reverse-DNS / ip fallback)",
              all(p.get("host") for p in st["players"]))
        check("per-node telemetry has ip + idle_s (STORY-04)",
              all("ip" in p and "idle_s" in p for p in st["players"]))
        check("players listed in ring order",
              st["ring"] == [p["id"] for p in st["players"]])
        with urllib.request.urlopen(f"http://{HOST}:8099/", timeout=2) as r:
            page = r.read().decode("utf-8")
        check("HTML page is the ring viz (svg + polls status.json)",
              "<svg" in page and "status.json" in page)

        print("drop + reconnect:")
        a.close()
        time.sleep(0.5)
        check("ring re-forms after drop (1 online)", status(8099)["players_online"] == 1)
        c = conn(5099)
        time.sleep(0.3)
        check("reconnect rejoins (2 online)", status(8099)["players_online"] == 2)
        b.sendall(b"\x77")
        check("relay after reconnect", recv_exact(c, 1) == b"\x77")
        b.close()
        c.close()

    # Phase B — the per-IP dedup classification: a reconnect supersedes a node
    # only on a *private* network IP (a LAN node = one IP), never public (a NAT
    # gateway may hide many players) or loopback (local testing). Unit-tested
    # directly, since the test host only has loopback to connect from.
    print("one-connection-per-private-IP classification:")
    import orchestrator as orch  # same directory

    check("192.168/16 (LAN) -> dedup", orch._should_dedup_ip("192.168.1.50") is True)
    check("10/8 (LAN) -> dedup", orch._should_dedup_ip("10.0.0.5") is True)
    check("172.16/12 (LAN) -> dedup", orch._should_dedup_ip("172.16.4.9") is True)
    check("public -> no dedup (NAT may hide many)", orch._should_dedup_ip("8.8.8.8") is False)
    check("loopback -> no dedup (local testing)", orch._should_dedup_ip("127.0.0.1") is False)
    check("invalid -> no dedup", orch._should_dedup_ip("not-an-ip") is False)

    # Reconnection supersede (EPIC-11 STORY-02): a prior same-IP connection that
    # has gone quiet past RECONNECT_STALE_S is stalled, so a reconnection drops it
    # and the new connection takes a fresh, incremented node id.
    p = orch.Player(id=9, peer="x:1", ip="x", conn=None, connected_at=0.0, last_active=100.0)
    check("fresh node not stalled", orch._is_stalled(p, 105.0) is False)
    check("quiet node stalled past threshold",
          orch._is_stalled(p, 100.0 + orch.RECONNECT_STALE_S + 1) is True)

    # Phase C — the --inspect protocol decoder (the only protocol awareness left
    # after EPIC-11 STORY-01 returned the relay to dumb). Read-only, off the relay
    # path — it decodes a player's OUT stream into event labels for the log.
    print("--inspect protocol decoder:")
    insp = orch.MidiMazeInspector()
    check("0x80 -> COUNT-PLAYERS-start", insp.feed(b"\x80") == ["COUNT-PLAYERS-start"])
    check("count byte -> COUNT-PLAYERS(n=2)", insp.feed(b"\x02") == ["COUNT-PLAYERS(n=2)"])
    check("0x84 -> START-GAME", insp.feed(b"\x84") == ["START-GAME"])
    check("0x82 -> TERMINATE-GAME", insp.feed(b"\x82") == ["TERMINATE-GAME"])
    check("0x86 -> NAME-DIALOG", insp.feed(b"\x86") == ["NAME-DIALOG"])

    # Phase D — the stdlib RFC 6455 codec (EPIC-13 STORY-02), unit-tested in
    # isolation before it is wired into the listener (STORY-03).
    print("websocket codec (RFC 6455, stdlib):")
    import ast

    # Handshake accept value: the canonical RFC 6455 4.2.2 example vector.
    check("Sec-WebSocket-Accept matches the RFC vector",
          ws.accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")
    resp = ws.handshake_response("dGhlIHNhbXBsZSBub25jZQ==")
    check("101 response carries the accept header",
          b"HTTP/1.1 101" in resp and b"s3pPLMBiTxaQ9kYGzzhZRbK+xOo=" in resp)
    check("is_upgrade detects a websocket request",
          ws.is_upgrade({"upgrade": "websocket", "connection": "keep-alive, Upgrade"}) is True)

    # Encode (server, unmasked) -> decode round-trip; 200 bytes exercises the 16-bit length.
    payload = bytes(range(200))
    check("server binary frame round-trips",
          ws.FrameDecoder().feed(ws.binary_frame(payload)) == [(ws.OP_BINARY, payload)])

    # A client-to-server frame is masked; it must decode to the plaintext.
    masked = ws.binary_frame(b"\x00\x80\x01", mask_key=b"\x37\xfa\x21\x3d")
    check("masked client frame: mask bit set", (masked[1] & 0x80) != 0)
    check("masked client frame decodes to plaintext",
          ws.FrameDecoder().feed(masked) == [(ws.OP_BINARY, b"\x00\x80\x01")])

    # A frame split across two feeds reassembles (TCP can split anywhere).
    wire = ws.binary_frame(b"maze-bytes")
    dec = ws.FrameDecoder()
    check("partial feed yields nothing yet", dec.feed(wire[:3]) == [])
    check("remainder completes the frame", dec.feed(wire[3:]) == [(ws.OP_BINARY, b"maze-bytes")])

    # Two frames in one read both come out, in order.
    check("two frames in one read decode in order",
          ws.FrameDecoder().feed(ws.binary_frame(b"AA") + ws.binary_frame(b"BB"))
          == [(ws.OP_BINARY, b"AA"), (ws.OP_BINARY, b"BB")])

    # Control frames carry the right opcodes.
    check("pong frame has the pong opcode", (ws.pong_frame(b"hi")[0] & 0x0F) == ws.OP_PONG)
    check("close frame has the close opcode", (ws.close_frame()[0] & 0x0F) == ws.OP_CLOSE)

    # Stdlib-only guard: ws.py imports nothing beyond hashlib, base64, struct.
    ws_src = (Path(__file__).resolve().parent / "ws.py").read_text()
    imported = set()
    for node in ast.walk(ast.parse(ws_src)):
        if isinstance(node, ast.Import):
            imported.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    imported.discard("__future__")
    check("ws.py is stdlib-only (hashlib/base64/struct)",
          imported <= {"hashlib", "base64", "struct"})

    # Phase E — a mixed ring (EPIC-13 STORY-03): with --ws, a TCP player and a
    # WebSocket player join one ring and relay to each other byte-exact.
    with server(5097, 8097, "--ws", "--ws-port", "5096"):
        print("mixed ring (TCP + WebSocket):")
        t = conn(5097)  # TCP player joins first -> ring order [t, w]
        w, ok = ws_connect(5096)  # WebSocket player second
        check("ws handshake completed (101 + accept)", ok)
        wdec = ws.FrameDecoder()
        time.sleep(0.3)

        st = status(8097)
        check("2 players online (tcp + ws)", st["players_online"] == 2)
        check("status reports transport per node",
              sorted(p.get("transport") for p in st["players"]) == ["tcp", "ws"])

        t.sendall(b"\x00\x84\x10")  # t's OUT -> w's IN (t -> next is w)
        check("TCP node OUT relays to WebSocket node IN",
              ws_recv(w, wdec, 3) == b"\x00\x84\x10")
        ws_send(w, b"\x99\x42")  # w's OUT -> t's IN (w is last, wraps to t)
        check("WebSocket node OUT relays to TCP node IN", recv_exact(t, 2) == b"\x99\x42")

        # A disconnect removes the node from the ring/status (not left displayed).
        w.close()
        time.sleep(0.5)
        st2 = status(8097)
        check("WebSocket node removed on disconnect (1 online)",
              st2["players_online"] == 1)
        check("the node left in the ring is the TCP one",
              len(st2["players"]) == 1 and st2["players"][0]["transport"] == "tcp")
        t.close()

    # Phase F — private rooms (EPIC-14 STORY-02): WS nodes that present the same
    # room key (Authorization: Bearer) share a ring; a different room is isolated.
    # Rooms are pre-provisioned over REST (STORY-03), so create them first.
    with server(5089, 8089, "--ws", "--ws-port", "5088", "--admin-key", "K"):
        print("private rooms (per-room rings):")
        for r in ("ALPHA", "BETA"):
            http_req(8089, "POST", "/rooms",
                     json.dumps({"key": r}).encode(), {"X-Admin-Key": "K"})
        a1, ok1 = ws_connect(5088, room="ALPHA")
        a2, ok2 = ws_connect(5088, room="ALPHA")
        b1, okb = ws_connect(5088, room="BETA")
        check("room handshakes completed", ok1 and ok2 and okb)
        da2 = ws.FrameDecoder()
        db1 = ws.FrameDecoder()
        time.sleep(0.3)

        # Same room: a1's OUT reaches a2's IN.
        ws_send(a1, b"\x11\x22\x33")
        check("same-room relay (ALPHA: a1 -> a2)", ws_recv(a2, da2, 3) == b"\x11\x22\x33")

        # Cross-room isolation: the BETA node sees none of ALPHA's traffic.
        b1.settimeout(0.5)
        leaked = b""
        try:
            for op, pl in db1.feed(b1.recv(4096)):
                if op in (ws.OP_BINARY, ws.OP_CONT):
                    leaked += pl
        except (socket.timeout, OSError):
            pass
        check("cross-room isolation (BETA sees no ALPHA traffic)", leaked == b"")

        # The other room is its own ring (a lone node echoes to itself).
        ws_send(b1, b"\x99")
        check("other room is its own ring (BETA echoes to self)",
              ws_recv(b1, db1, 1) == b"\x99")
        a1.close()
        a2.close()
        b1.close()

    # Phase G — room provisioning over REST (EPIC-14 STORY-03): admin-guarded
    # writes, reject-unknown on join, list, and delete.
    with server(5085, 8085, "--ws", "--ws-port", "5084", "--admin-key", "SECRET"):
        print("room provisioning (REST):")
        code, _ = http_req(8085, "POST", "/rooms", b'{"key":"ALPHA"}')
        check("POST without admin key refused (403)", code == 403)
        code, _ = http_req(8085, "POST", "/rooms", b'{"key":"ALPHA"}',
                           {"X-Admin-Key": "SECRET"})
        check("POST with admin key creates the room", code == 200)
        code, body = http_req(8085, "GET", "/rooms")
        check("GET /rooms lists the new room",
              code == 200 and any(r["room"] == "ALPHA"
                                  for r in json.loads(body)["rooms"]))
        a, oka = ws_connect(5084, room="ALPHA")
        check("join a provisioned room succeeds", oka)
        g, okg = ws_connect(5084, room="GHOST")
        check("join an unprovisioned room is refused", not okg)
        a.close()
        try:
            g.close()
        except OSError:
            pass
        code, _ = http_req(8085, "DELETE", "/rooms/ALPHA", None, {"X-Admin-Key": "SECRET"})
        check("DELETE with admin key removes the room", code == 200)
        code, body = http_req(8085, "GET", "/rooms")
        check("deleted room no longer listed",
              all(r["room"] != "ALPHA" for r in json.loads(body)["rooms"]))

    # Phase H — room lifecycle (EPIC-14 STORY-04): 16-player cap, auto codes,
    # empty-room TTL reaper. A short --room-ttl keeps the reaper test fast.
    with server(5083, 8083, "--ws", "--ws-port", "5082", "--admin-key", "K",
                "--room-ttl", "1"):
        print("room lifecycle (cap / auto-code / TTL):")
        http_req(8083, "POST", "/rooms", b'{"key":"FULL"}', {"X-Admin-Key": "K"})
        socks = []
        for _ in range(16):
            s, ok = ws_connect(5082, room="FULL")
            if ok:
                socks.append(s)
        time.sleep(0.5)
        _, body = http_req(8083, "GET", "/rooms")
        cnt = next((r["players"] for r in json.loads(body)["rooms"] if r["room"] == "FULL"), 0)
        check("room fills to the 16-player cap", len(socks) == 16 and cnt == 16)
        s17, ok17 = ws_connect(5082, room="FULL")
        check("the 17th join is refused (cap)", not ok17)
        for s in socks:
            s.close()
        try:
            s17.close()
        except OSError:
            pass

        # Auto-generated code: POST with no key returns a usable room code.
        code, body = http_req(8083, "POST", "/rooms", b"", {"X-Admin-Key": "K"})
        auto = json.loads(body).get("room", "")
        check("POST with no key mints a room code", code == 200 and 1 <= len(auto) <= 16)
        ac, okac = ws_connect(5082, room=auto)
        check("the auto code is joinable", okac)
        ac.close()

        # Empty-room TTL: a used room that empties is reaped (ttl=1s).
        http_req(8083, "POST", "/rooms", b'{"key":"TEMP"}', {"X-Admin-Key": "K"})
        tmp, oktmp = ws_connect(5082, room="TEMP")
        check("temp room joinable before reap", oktmp)
        tmp.close()  # room TEMP is now used and empty
        time.sleep(3.5)
        _, body = http_req(8083, "GET", "/rooms")
        check("empty used room is reaped after the TTL",
              all(r["room"] != "TEMP" for r in json.loads(body)["rooms"]))

    # Phase I — room-aware status + UI (EPIC-14 STORY-06): status.json?room scopes
    # to a room, the default room is separate, and the page carries a room selector.
    with server(5081, 8081, "--ws", "--ws-port", "5080", "--admin-key", "K"):
        print("room-aware status + UI:")
        http_req(8081, "POST", "/rooms", b'{"key":"ALPHA"}', {"X-Admin-Key": "K"})
        wsa = ws_connect(5080, room="ALPHA")[0]
        tcp = conn(5081)  # TCP node -> default room
        time.sleep(0.3)
        sj_a = json.loads(http_req(8081, "GET", "/status.json?room=ALPHA")[1])
        check("status.json?room scopes to the room",
              sj_a["room"] == "ALPHA" and sj_a["players_online"] == 1)
        sj_d = json.loads(http_req(8081, "GET", "/status.json")[1])
        check("status.json with no param is the default room",
              sj_d["room"] == "" and sj_d["players_online"] == 1)
        page = http_req(8081, "GET", "/")[1].decode("utf-8")
        check("ring view has a room selector polling rooms",
              "<select id='room'" in page and "fetch('rooms'" in page)
        wsa.close()
        tcp.close()

    print()
    if _failures:
        print(f"FAIL — {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("PASS: orchestrator relay + IP-dedup + --inspect + ws codec + mixed ring + rooms + REST")
    return 0


if __name__ == "__main__":
    sys.exit(main())
