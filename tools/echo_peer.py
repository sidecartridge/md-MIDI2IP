#!/usr/bin/env python3
"""Dev echo peer for EPIC-03 STORY-01 / STORY-05 validation.

Accepts a TCP connection from the RP firmware and echoes every byte straight
back — a network stand-in for the EPIC-02 RP-local loopback. It proves the wire
works (the RP reaches "up" and bytes round-trip ST -> RP -> network -> RP -> ST).

It does NOT play MIDI Maze (D-09): a single node can't start a match — that needs
a real 2nd node from the orchestrator. This is only for validating the transport.

Run on a machine on the same LAN as the Pico W, then set MIDI_NET_HOST in
rp/src/midi.c to this machine's IP and reflash.

Usage:  python3 tools/echo_peer.py [port]      (default 5005)
"""
import socket
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5005

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("0.0.0.0", PORT))
srv.listen(1)
print(f"echo peer listening on 0.0.0.0:{PORT}  (Ctrl-C to quit)")

while True:
    conn, addr = srv.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"connected: {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            conn.sendall(data)
            print(f"echoed {len(data)} byte(s): {data.hex()}")
    except ConnectionError as exc:
        print(f"connection error: {exc}")
    finally:
        conn.close()
        print("disconnected; waiting for next connection")
