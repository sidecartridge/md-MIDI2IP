#!/usr/bin/env python3
"""Hatari gateway self-test — EPIC-05.

  STORY-01: FIFO lifecycle — create (idempotent), robust open tolerant of Hatari
    starting before or after the gateway, cleanup.
  STORY-02: bridge — raw bytes pump both ways between the FIFOs and the
    orchestrator socket (fake Hatari on the FIFO ends, a socketpair standing in
    for the orchestrator).

Stdlib only; exit 0 = PASS.

Usage:  python3 hatari-gateway/selftest.py
"""
import errno
import os
import socket
import stat
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gateway  # noqa: E402

_failures: "list[str]" = []


def check(name: str, ok: bool) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        _failures.append(name)


def _fake_hatari_open(out_path: str, in_path: str) -> "tuple[int, int]":
    """Open the ends Hatari would: read midi_in.fifo (--midi-in), write
    midi_out.fifo (--midi-out, retry until the gateway's reader exists)."""
    h_in = os.open(in_path, os.O_RDONLY | os.O_NONBLOCK)
    for _ in range(200):
        try:
            h_out = os.open(out_path, os.O_WRONLY | os.O_NONBLOCK)
            return h_in, h_out
        except OSError as exc:
            if exc.errno != errno.ENXIO:
                raise
            time.sleep(0.02)
    raise RuntimeError("could not open midi_out.fifo for writing")


def _read_nonblock(fd: int, n: int, timeout: float = 1.0) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            data = os.read(fd, n)
            if data:
                return data
        except BlockingIOError:
            pass
        time.sleep(0.02)
    return b""


def test_fifo_lifecycle() -> None:
    print("STORY-01 — FIFO lifecycle:")
    d = tempfile.mkdtemp(prefix="hatari-gw-fifo-")
    try:
        out_path, in_path = gateway.create_fifos(d)
        check("midi_out.fifo is a FIFO", stat.S_ISFIFO(os.stat(out_path).st_mode))
        check("midi_in.fifo is a FIFO", stat.S_ISFIFO(os.stat(in_path).st_mode))
        check("create_fifos idempotent", gateway.create_fifos(d) == (out_path, in_path))

        result: dict = {}

        def run_open() -> None:
            result["fds"] = gateway.open_fifos(out_path, in_path, poll=0.02)

        t = threading.Thread(target=run_open, daemon=True)
        t.start()
        time.sleep(0.3)
        check("open blocks until Hatari opens the IN fifo", "fds" not in result)
        reader = os.open(in_path, os.O_RDONLY | os.O_NONBLOCK)
        t.join(timeout=3)
        check("open returns once the IN reader appears", "fds" in result)
        if "fds" in result:
            os.close(result["fds"][0])
            os.close(result["fds"][1])
        os.close(reader)
    finally:
        gateway.remove_fifos(d)
        try:
            os.rmdir(d)
        except OSError:
            pass


def test_bridge() -> None:
    print("STORY-02 — bridge (FIFO <-> socket, both ways):")
    d = tempfile.mkdtemp(prefix="hatari-gw-bridge-")
    out_fd = in_fd = None
    h_in = h_out = None
    gw_sock = peer = None
    try:
        out_path, in_path = gateway.create_fifos(d)
        result: dict = {}

        def run_open() -> None:
            result["fds"] = gateway.open_fifos(out_path, in_path, poll=0.02)

        t = threading.Thread(target=run_open, daemon=True)
        t.start()
        h_in, h_out = _fake_hatari_open(out_path, in_path)
        t.join(timeout=3)
        out_fd, in_fd = result["fds"]

        gw_sock, peer = socket.socketpair()  # peer = stand-in orchestrator
        peer.settimeout(2.0)
        bt = threading.Thread(target=gateway.bridge, args=(out_fd, in_fd, gw_sock),
                              daemon=True)
        bt.start()

        os.write(h_out, b"\x42\x80")  # Atari MIDI OUT
        check("Atari OUT -> orchestrator", peer.recv(16) == b"\x42\x80")

        peer.sendall(b"\x99")  # orchestrator -> Atari MIDI IN
        check("orchestrator -> Atari IN", _read_nonblock(h_in, 16) == b"\x99")
    finally:
        for s in (peer, gw_sock):
            if s is not None:
                s.close()
        for fd in (h_in, h_out, out_fd, in_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        gateway.remove_fifos(d)
        try:
            os.rmdir(d)
        except OSError:
            pass


def main() -> int:
    test_fifo_lifecycle()
    test_bridge()
    print()
    if _failures:
        print(f"FAIL — {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("PASS — Hatari gateway FIFO lifecycle + bridge validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
