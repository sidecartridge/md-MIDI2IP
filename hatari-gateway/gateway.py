#!/usr/bin/env python3
"""Hatari gateway — EPIC-05.

A software RP2040 for the Hatari emulator: bridges Hatari's file-based raw MIDI
to the MIDI-to-IP orchestrator (EPIC-04), so MIDI Maze running in Hatari becomes
a virtual player. Python 3 **standard library only** — no third-party packages.

Hatari's MIDI file flags (these enable MIDI on their own — there is no separate
`--midi` flag in Hatari 2.6.1):
  --midi-out <file> : Hatari WRITES the Atari's MIDI OUT here   (Atari -> host)
  --midi-in  <file> : Hatari READS the Atari's MIDI IN from here (host  -> Atari)
So we use two FIFOs:
  midi_out.fifo : Atari MIDI OUT -> the gateway READS  (Hatari's --midi-out)
  midi_in.fifo  : Atari MIDI IN  -> the gateway WRITES (Hatari's --midi-in)

Scope so far:
  - STORY-01: create the FIFOs, document the Hatari invocation, open both ends
    robustly (non-blocking, any start order).
  - STORY-02: the bridge — pump raw bytes both ways between the FIFOs and the
    orchestrator socket (select-driven, single-thread, verbatim).
The orchestrator client lifecycle (connect / reconnect / status) is STORY-03.

Usage:  python3 hatari-gateway/gateway.py [--dir DIR]
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import os
import select
import socket
import stat
import time

FIFO_OUT = "midi_out.fifo"  # Atari MIDI OUT: gateway reads  (Hatari --midi-out)
FIFO_IN = "midi_in.fifo"    # Atari MIDI IN:  gateway writes (Hatari --midi-in)


def create_fifos(dirpath: str) -> tuple[str, str]:
    """Create both FIFOs (idempotent). Returns (out_path, in_path)."""
    os.makedirs(dirpath, exist_ok=True)
    out_path = os.path.join(dirpath, FIFO_OUT)
    in_path = os.path.join(dirpath, FIFO_IN)
    for path in (out_path, in_path):
        if not os.path.exists(path):
            os.mkfifo(path)
        elif not stat.S_ISFIFO(os.stat(path).st_mode):
            raise SystemExit(f"{path} exists and is not a FIFO")
    return out_path, in_path


def hatari_command(dirpath: str) -> str:
    """The Hatari invocation for these FIFOs. --midi-out is the Atari's OUT
    (Hatari writes); --midi-in is the Atari's IN (Hatari reads)."""
    out_path = os.path.join(dirpath, FIFO_OUT)
    in_path = os.path.join(dirpath, FIFO_IN)
    return f"hatari --midi-out {out_path} --midi-in {in_path} <disk-or-program>"


def open_fifos(out_path: str, in_path: str, poll: float = 0.2) -> tuple[int, int]:
    """Open both FIFO ends, tolerant of Hatari starting before or after us.

    OUT (Atari MIDI OUT, we read): ``O_RDONLY | O_NONBLOCK`` succeeds at once.
    IN  (Atari MIDI IN,  we write): ``O_WRONLY | O_NONBLOCK`` raises ENXIO until
    Hatari opens it for reading (its ``--midi-in``) — we retry until it does.
    Blocks until both ends are connected. Returns (out_fd, in_fd)."""
    out_fd = os.open(out_path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        while True:
            try:
                in_fd = os.open(in_path, os.O_WRONLY | os.O_NONBLOCK)
                return out_fd, in_fd
            except OSError as exc:
                if exc.errno != errno.ENXIO:
                    raise
                time.sleep(poll)  # no reader yet (Hatari not up) — wait
    except BaseException:
        os.close(out_fd)
        raise


def _set_blocking(fd: int) -> None:
    fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) & ~os.O_NONBLOCK)


def _write_all(fd: int, data: bytes) -> None:
    """os.write may write fewer bytes than requested — loop so we never drop
    MIDI bytes (a dropped byte desyncs the ring -> 'MIDI ring boo boo')."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def bridge(out_fd: int, in_fd: int, sock: socket.socket) -> None:
    """STORY-02: pump raw bytes both ways until either end closes, then return.

      Atari MIDI OUT (out_fd, read) -> orchestrator (sock)
      orchestrator (sock)          -> Atari MIDI IN  (in_fd, write)

    Verbatim, in order, no parsing (D-02). select() drives readiness so reads
    never block; writes (sendall / os.write) may briefly block on backpressure,
    which is fine at MIDI rates. This is the software twin of the RP byte pipe:
    out_fd ~ CMD_MIDI_SEND, in_fd ~ CMD_MIDI_RECV -> Iorec."""
    _set_blocking(out_fd)
    _set_blocking(in_fd)
    sock.setblocking(True)
    while True:
        try:
            readable, _, _ = select.select([out_fd, sock], [], [])
        except (OSError, ValueError):
            return
        if out_fd in readable:
            data = os.read(out_fd, 4096)
            if not data:  # Hatari closed its MIDI-out
                return
            try:
                sock.sendall(data)
            except OSError:
                return
        if sock in readable:
            try:
                data = sock.recv(4096)
            except OSError:
                return
            if not data:  # orchestrator closed
                return
            try:
                _write_all(in_fd, data)
            except OSError:
                return


def remove_fifos(dirpath: str) -> None:
    for name in (FIFO_OUT, FIFO_IN):
        try:
            os.remove(os.path.join(dirpath, name))
        except FileNotFoundError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Hatari MIDI gateway (EPIC-05)")
    parser.add_argument(
        "--dir", default="/tmp/hatari-midi",
        help="directory for the MIDI FIFOs (default: /tmp/hatari-midi)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="orchestrator host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5005, help="orchestrator port (default: 5005)"
    )
    args = parser.parse_args()

    out_path, in_path = create_fifos(args.dir)
    print("FIFOs ready:")
    print(f"  {out_path}  (Atari MIDI OUT -> gateway)")
    print(f"  {in_path}  (gateway -> Atari MIDI IN)")
    print(f"\nLaunch Hatari with:\n  {hatari_command(args.dir)}\n")

    out_fd = in_fd = None
    sock = None
    try:
        print("waiting for Hatari to open the MIDI FIFOs ... (Ctrl-C to quit)")
        out_fd, in_fd = open_fifos(out_path, in_path)
        print("connected to Hatari.")
        print(f"connecting to orchestrator {args.host}:{args.port} ...")
        sock = socket.create_connection((args.host, args.port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print("connected to orchestrator — bridging. (reconnect is STORY-03)")
        bridge(out_fd, in_fd, sock)
        print("bridge ended (a side disconnected).")
    except KeyboardInterrupt:
        print("\nbye")
    except OSError as exc:
        print(f"error: {exc}")
    finally:
        if sock is not None:
            sock.close()
        if out_fd is not None:
            os.close(out_fd)
        if in_fd is not None:
            os.close(in_fd)
        remove_fifos(args.dir)


if __name__ == "__main__":
    main()
