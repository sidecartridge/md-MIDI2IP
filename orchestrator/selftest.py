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

    # Reconnection supersede (EPIC-11 STORY-02): a prior same-IP connection that
    # has gone quiet past RECONNECT_STALE_S is stalled, so a reconnection drops it
    # and the new connection takes a fresh, incremented node id.
    p = orch.Player(id=9, peer="x:1", ip="x", writer=None, connected_at=0.0, last_active=100.0)
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

    print()
    if _failures:
        print(f"FAIL — {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("PASS — orchestrator dumb relay + IP-dedup + --inspect decoder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
