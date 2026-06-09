---
id: STORY-02
epic: EPIC-03
title: Send OUT bytes to the orchestrator (replace the echo)
status: done
milestone: alpha-mvp
---

## Goal

Replace EPIC-02's local echo on the send side: in `midi.c`'s `CMD_MIDI_SEND`
handler, instead of `midi_in_push(byte)`, hand the byte to the network sender so
it reaches the orchestrator with low added latency.

## Tasks

- [x] On `CMD_MIDI_SEND`, `tcp_write` the byte to the socket (was the IN-queue echo) via `midi_net_send_byte`
- [x] Forward bytes verbatim — no MIDI parsing/filtering/framing (D-02)
- [x] Flush immediately with `tcp_output` (TCP_NODELAY) for lowest latency (C-01)
- [ ] Backpressure: currently drops on a full send buffer (fine at handshake rate); queue + retry on `tcp_sent` is a gameplay-rate refinement (EPIC-05)

## Acceptance

Bytes the ST emits via `Bconout(3)` appear at the orchestrator (or echo peer) in
order; measured added latency is within target (set in EPIC-05).

**Verified on hardware:** with `tools/echo_peer.py`, the peer prints the MIDI
Maze bytes (`00`, `80`, `01`, …) in order, and the ST becomes MASTER via the
network round-trip.

## Notes

`CMD_MIDI_SEND` is the exact echo seam from EPIC-02 STORY-03. The stream is opaque
bytes (D-02) — never reorder or drop. MIDI Maze is latency-sensitive (C-01):
coalesce only within a few ms.
