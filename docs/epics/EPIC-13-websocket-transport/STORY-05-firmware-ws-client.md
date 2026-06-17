---
id: STORY-05
epic: EPIC-13
title: Microfirmware WebSocket client transport
status: todo
---

## Goal

The RP reaches the orchestrator over WebSocket, carrying the same opaque MIDI byte
stream, reusing the existing connection state machine and backoff.

## Tasks

- [ ] After the TCP connect (`rp/src/midi.c:209-228`), when transport is `ws`, send the RFC 6455 client handshake: GET on the configured path with `Upgrade`, `Connection: Upgrade`, and a random `Sec-WebSocket-Key`; validate the 101 response and `Sec-WebSocket-Accept` before entering `MIDI_NET_UP`
- [ ] Frame MIDI OUT: wrap the bytes drained in `midi_net_flush_out` (`midi.c:252-275`) as masked binary frames (client frames must be masked, XOR with a fresh 4-byte key)
- [ ] De-frame MIDI IN: parse incoming frames in `midi_net_recv_cb` (`midi.c:159-184`), unwrap binary payloads into `midi_in_push`, reassembling frames split across pbufs
- [ ] Answer a server ping with a pong and treat a close frame as a connection reset (reuse the existing reconnect and backoff path)
- [ ] Gate all of this on the transport mode so the raw-TCP path is untouched when transport is `tcp`; keep the hot path allocation-free
- [ ] Confirm the 8 KB m68k cartridge budget is unaffected (this is RP-side C only) and record the RP flash cost

## Acceptance

With transport `ws` against an orchestrator started with `--ws`, the node connects, the
handshake completes, and MIDI flows both ways byte-exact. With transport `tcp` the
behavior is identical to today.

## Notes

No TLS: plain `ws` over the raw lwIP PCB (D-13). The mask key can come from the existing
random token or a cheap per-frame counter seeded at connect; masking is a byte-wise XOR.
Depends on a WebSocket-enabled orchestrator (STORY-03).
