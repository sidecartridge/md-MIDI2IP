"""RFC 6455 WebSocket codec, Python standard library only.

EPIC-13 STORY-02. Carries the orchestrator's opaque MIDI byte stream (D-02) over
WebSocket binary frames; the byte stream is unchanged, this is only the carrier
(D-13). No third-party packages: the handshake uses hashlib + base64, the framing
uses struct.

This module is the server-side codec. A client-to-server frame is masked (an RFC 6455
requirement); a server-to-client frame is unmasked. `encode_frame` takes an optional
mask key, so the same code can build masked client frames later (EPIC-13 STORY-04/06)
without pulling in a random-number import here.
"""
from __future__ import annotations

import base64
import hashlib
import struct

# RFC 6455 section 1.3: the GUID appended to Sec-WebSocket-Key before the SHA-1.
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Opcodes (RFC 6455 section 5.2).
OP_CONT = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA


class WSError(Exception):
    """A malformed or unsupported WebSocket frame."""


def accept_key(key: str) -> str:
    """Sec-WebSocket-Accept for a client's Sec-WebSocket-Key (RFC 6455 4.2.2)."""
    digest = hashlib.sha1((key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def handshake_response(key: str) -> bytes:
    """The HTTP 101 Switching Protocols response for a validated upgrade request."""
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key(key)}\r\n"
        "\r\n"
    ).encode("ascii")


def client_handshake_request(host: str, path: str, key: str, room: str = "") -> bytes:
    """The client GET Upgrade request for a server handshake (EPIC-13 STORY-04/06).
    The caller supplies a base64 Sec-WebSocket-Key (16 random bytes); key generation
    stays with the caller so this module needs no random-number import. A non-empty
    `room` is sent as Authorization: Bearer to join a private room (EPIC-14)."""
    auth = f"Authorization: Bearer {room}\r\n" if room else ""
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"{auth}"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("latin-1")


def parse_headers(raw: bytes) -> dict[str, str]:
    """Parse an HTTP header block (after the request line) into a lowercased dict."""
    headers: dict[str, str] = {}
    for line in raw.split(b"\r\n"):
        if not line or b":" not in line:
            continue
        name, _, value = line.partition(b":")
        headers[name.decode("latin-1").strip().lower()] = value.decode("latin-1").strip()
    return headers


def is_upgrade(headers: dict[str, str]) -> bool:
    """True if parsed headers request a WebSocket upgrade."""
    return (
        headers.get("upgrade", "").lower() == "websocket"
        and "upgrade" in headers.get("connection", "").lower()
    )


def encode_frame(opcode: int, payload: bytes = b"", *, mask_key: bytes | None = None) -> bytes:
    """Encode one final (FIN=1) frame. Unmasked unless a 4-byte mask_key is given."""
    if mask_key is not None and len(mask_key) != 4:
        raise WSError("mask key must be 4 bytes")
    n = len(payload)
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))  # FIN set + opcode
    mask_bit = 0x80 if mask_key is not None else 0x00
    if n < 126:
        header.append(mask_bit | n)
    elif n < 65536:
        header.append(mask_bit | 126)
        header += struct.pack(">H", n)
    else:
        header.append(mask_bit | 127)
        header += struct.pack(">Q", n)
    if mask_key is None:
        return bytes(header) + payload
    masked = bytes(payload[i] ^ mask_key[i & 3] for i in range(n))
    return bytes(header) + mask_key + masked


def binary_frame(payload: bytes, *, mask_key: bytes | None = None) -> bytes:
    return encode_frame(OP_BINARY, payload, mask_key=mask_key)


def pong_frame(payload: bytes = b"", *, mask_key: bytes | None = None) -> bytes:
    return encode_frame(OP_PONG, payload, mask_key=mask_key)


def close_frame(code: int = 1000, reason: bytes = b"", *, mask_key: bytes | None = None) -> bytes:
    return encode_frame(OP_CLOSE, struct.pack(">H", code) + reason, mask_key=mask_key)


class FrameDecoder:
    """Streaming RFC 6455 frame parser.

    Feed it bytes as they arrive off the socket. It returns each complete frame as an
    `(opcode, payload)` pair and buffers any partial frame until the rest arrives, so a
    frame split across TCP reads reassembles. Masked client payloads are unmasked.
    Control frames (close, ping, pong) come back alongside data frames so the caller can
    answer a ping and act on a close. A data message fragmented across continuation
    frames arrives as a binary frame followed by `OP_CONT` frames; for an opaque byte
    pipe the caller forwards both payloads in order.
    """

    def __init__(self, max_payload: int = 1 << 20) -> None:
        self._buf = bytearray()
        self._max = max_payload

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        self._buf.extend(data)
        frames: list[tuple[int, bytes]] = []
        while True:
            frame = self._next()
            if frame is None:
                break
            frames.append(frame)
        return frames

    def _next(self) -> tuple[int, bytes] | None:
        b = self._buf
        if len(b) < 2:
            return None
        opcode = b[0] & 0x0F
        masked = (b[1] & 0x80) != 0
        length = b[1] & 0x7F
        idx = 2
        if length == 126:
            if len(b) < idx + 2:
                return None
            length = struct.unpack_from(">H", b, idx)[0]
            idx += 2
        elif length == 127:
            if len(b) < idx + 8:
                return None
            length = struct.unpack_from(">Q", b, idx)[0]
            idx += 8
        if length > self._max:
            raise WSError(f"frame payload too large: {length}")
        mask = b""
        if masked:
            if len(b) < idx + 4:
                return None
            mask = bytes(b[idx:idx + 4])
            idx += 4
        if len(b) < idx + length:
            return None
        payload = bytes(b[idx:idx + length])
        if masked:
            payload = bytes(payload[i] ^ mask[i & 3] for i in range(length))
        del b[: idx + length]
        return (opcode, payload)
