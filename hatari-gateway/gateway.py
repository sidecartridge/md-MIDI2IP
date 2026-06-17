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

EPIC-13 STORY-04: an optional `--transport ws` carries the same bytes over a
WebSocket (D-13), reusing the orchestrator's stdlib RFC 6455 codec (`ws.py`).
This is the known-good client that proves the WebSocket path before the firmware.

Usage:  python3 hatari-gateway/gateway.py [--dir DIR] [--transport tcp|ws]
"""
from __future__ import annotations

import argparse
import base64
import errno
import fcntl
import os
import select
import socket
import stat
import sys
import time

# Reuse the orchestrator's RFC 6455 codec (single source of truth, EPIC-13).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "orchestrator"))
import ws  # noqa: E402

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


class _WsSocket:
    """Wrap a connected socket so `bridge()` keeps using sendall/recv/fileno while
    the bytes ride WebSocket frames (EPIC-13 STORY-04). A client-to-server frame is
    masked (RFC 6455); recv decodes server frames, answers a ping with a pong, and
    reports EOF on a close frame. The codec is the orchestrator's `ws.py`."""

    def __init__(self, sock: socket.socket, initial: bytes = b"") -> None:
        self._sock = sock
        self._dec = ws.FrameDecoder()
        self._initial = initial  # frame bytes that trailed the handshake response

    def fileno(self) -> int:
        return self._sock.fileno()

    def setblocking(self, flag: bool) -> None:
        self._sock.setblocking(flag)

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(ws.binary_frame(data, mask_key=os.urandom(4)))

    def recv(self, n: int) -> bytes:
        while True:
            if self._initial:
                raw, self._initial = self._initial, b""
            else:
                raw = self._sock.recv(n)
                if not raw:
                    return b""  # TCP EOF
            out = bytearray()
            for opcode, payload in self._dec.feed(raw):
                if opcode in (ws.OP_BINARY, ws.OP_CONT, ws.OP_TEXT):
                    out.extend(payload)
                elif opcode == ws.OP_PING:
                    self._sock.sendall(ws.pong_frame(payload, mask_key=os.urandom(4)))
                elif opcode == ws.OP_CLOSE:
                    return b""  # server asked to close
            if out:
                return bytes(out)
            # only control frames this read: loop for more (server sends data or close)

    def close(self) -> None:
        self._sock.close()


def ws_handshake(sock: socket.socket, host: str, port: int, path: str = "/") -> _WsSocket:
    """Run the RFC 6455 client handshake on a connected socket and return a framed
    wrapper. Raises ConnectionError if the server does not answer 101 with the
    expected Sec-WebSocket-Accept."""
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    sock.sendall(ws.client_handshake_request(f"{host}:{port}", path, key))
    sock.settimeout(5.0)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("server closed during the WebSocket handshake")
        buf += chunk
    header, _, rest = buf.partition(b"\r\n\r\n")
    if b" 101 " not in header or ws.accept_key(key).encode("ascii") not in header:
        raise ConnectionError("WebSocket handshake failed (no 101 / bad accept)")
    sock.settimeout(None)
    return _WsSocket(sock, initial=rest)


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
    parser.add_argument(
        "--transport", choices=("tcp", "ws"), default="tcp",
        help="carrier to the orchestrator: tcp (default) or ws (WebSocket, D-13). "
             "Use ws to reach an orchestrator started with --ws.",
    )
    parser.add_argument(
        "--ws-path", default="/", help="WebSocket request path when --transport ws (default: /)",
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
        print(f"connecting to orchestrator {args.host}:{args.port} ({args.transport}) ...")
        sock = socket.create_connection((args.host, args.port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if args.transport == "ws":
            sock = ws_handshake(sock, args.host, args.port, args.ws_path)
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
