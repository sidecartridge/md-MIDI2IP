#!/usr/bin/env python3
"""Dev echo peer for EPIC-03 STORY-01 / STORY-05 validation.

Accepts a TCP connection from the RP firmware and echoes every byte back — a
network stand-in for the EPIC-02 RP-local loopback. It proves the wire works (the
RP reaches "up" and bytes round-trip ST -> RP -> network -> RP -> ST). It does NOT
play MIDI Maze (D-09): a single node can't start a match.

Robust to the RP dying ungracefully (reset / reflash / power loss), which sends
no TCP FIN:
  - a new connection from the rebooted RP supersedes the stale socket at once;
  - TCP keepalive detects a silently-dead idle link within ~10 s;
  - a send/recv error is caught and the link is dropped.

Run on the same LAN as the Pico W, then set MIDI_NET_HOST in rp/src/midi.c to
this machine's IP and reflash.

Usage:  python3 tools/echo_peer.py [port]      (default 5005)
"""
import select
import socket
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5005


def enable_keepalive(sock):
    """Detect a silently-dead peer in ~10 s instead of TCP's multi-hour default."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if hasattr(socket, "TCP_KEEPIDLE"):  # Linux
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    elif hasattr(socket, "TCP_KEEPALIVE"):  # macOS: seconds idle before probing
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 5)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(1)
    print(f"echo peer listening on 0.0.0.0:{PORT}  (Ctrl-C to quit)")

    client = None
    addr = None
    while True:
        watch = [srv] if client is None else [srv, client]
        readable, _, _ = select.select(watch, [], [], 1.0)

        for sock in readable:
            if sock is srv:
                conn, conn_addr = srv.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                enable_keepalive(conn)
                if client is not None:
                    # The RP reconnected without closing the old socket — it must
                    # have reset / reflashed. Drop the stale connection.
                    print(f"new client {conn_addr} — dropping stale {addr}")
                    client.close()
                client, addr = conn, conn_addr
                print(f"connected: {addr}")
                continue

            # Data — or death — on the client socket.
            data = b""
            try:
                data = client.recv(4096)
                if data:
                    client.sendall(data)
            except OSError as exc:
                print(f"disconnected: {addr} (error: {exc})")
                client.close()
                client, addr = None, None
                continue
            if not data:  # clean close (FIN): recv returns empty
                print(f"disconnected: {addr} (peer closed)")
                client.close()
                client, addr = None, None
                continue
            print(f"echoed {len(data)} byte(s): {data.hex()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nbye")
