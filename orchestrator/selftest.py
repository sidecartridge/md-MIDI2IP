#!/usr/bin/env python3
"""Orchestrator self-test — EPIC-04 STORY-05.

Spawns orchestrator.py on test ports and validates it end to end:
  Phase A (ring): two clients form a 2-ring; A<->B byte-exact; HTTP /status.json
    reflects players + ring; a drop re-forms the ring and a reconnect rejoins.
    (Both clients are on loopback, which is exempt from the per-IP dedup.)
  Phase B (dedup classification): one-connection-per-IP applies to private LAN
    addresses only — not public (NAT may hide many) or loopback (local testing).

Stdlib only. Exit code 0 = PASS, 1 = FAIL.

Usage:  python3 orchestrator/selftest.py
"""
import json
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

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

    # Phase C — EPIC-08 STORY-01 ring protocol-state model (no hardware): feed
    # recorded MIDI Maze byte sequences and assert the inferred phase/master/count.
    print("ring protocol-state model (EPIC-08 STORY-01):")
    r = orch.RingState()
    r.add_player(1)
    r.add_player(2)
    check("2 players -> electing", r.snapshot()["phase"] == "electing")
    r.feed(1, b"\x00")
    r.feed(2, b"\x00")
    check("master election keeps electing", r.snapshot()["phase"] == "electing")
    r.feed(1, b"\x80\x02")  # player 1 originates COUNT-PLAYERS(n=2)
    snap = r.snapshot()
    check("count -> counting", snap["phase"] == "counting")
    check("count master = originator (p1)", snap["master"] == 1)
    check("count value parsed (2)", snap["last_count"] == 2)
    r.feed(1, b"\x84")  # START-GAME (master only)
    check("start-game -> in-game", r.snapshot()["phase"] == "in-game")
    r.feed(1, b"\x82")  # TERMINATE-GAME
    check("terminate -> terminated", r.snapshot()["phase"] == "terminated")
    r.add_player(3)  # membership change must reset the round (D-04)
    reset = r.snapshot()
    check("join resets phase to electing", reset["phase"] == "electing")
    check("join clears master", reset["master"] is None)
    check("join clears last count", reset["last_count"] is None)

    print()
    if _failures:
        print(f"FAIL — {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("PASS — orchestrator ring + IP-dedup + protocol-state model validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
