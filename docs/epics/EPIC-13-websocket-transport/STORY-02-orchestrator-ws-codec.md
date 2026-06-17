---
id: STORY-02
epic: EPIC-13
title: Orchestrator stdlib WebSocket handshake and frame codec
status: todo
---

## Goal

A self-contained, tested RFC 6455 implementation on the Python standard library: the
server handshake plus a streaming binary-frame encoder and decoder, with no third-party
packages.

## Tasks

- [ ] Implement the server handshake: parse the GET request line and headers, compute `Sec-WebSocket-Accept` as base64(sha1(key + RFC6455 GUID)), and return the 101 Switching Protocols response (`hashlib` + `base64`, stdlib)
- [ ] Implement a streaming frame decoder that reassembles frames split across TCP reads, unmasks client payloads, handles the binary / continuation / ping / pong / close opcodes, and yields payload bytes in order
- [ ] Implement a frame encoder for server-to-client binary frames (unmasked) plus a pong and a close responder
- [ ] Add selftest coverage: a known-vector handshake accept value, an encode then decode round-trip, a masked client frame decoded correctly, and one frame split across two reads reassembled correctly
- [ ] Keep it stdlib only: assert no import beyond `hashlib`, `base64`, `struct` is added

## Acceptance

`orchestrator/selftest.py` passes the handshake vector and the framing round-trips,
including masked input and a split frame. No third-party import is introduced.

## Notes

This story produces the codec in isolation so it is unit-testable before wiring. The
handshake intercept point is the existing hand-rolled HTTP reader
(`orchestrator/orchestrator.py:478-513`).
