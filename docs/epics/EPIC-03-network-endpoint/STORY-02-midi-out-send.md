---
id: STORY-02
epic: EPIC-03
title: Send OUT bytes to the orchestrator (replace the echo)
status: todo
milestone: alpha-mvp
---

## Goal

Replace EPIC-02's local echo on the send side: in `midi.c`'s `CMD_MIDI_SEND`
handler, instead of `midi_in_push(byte)`, hand the byte to the network sender so
it reaches the orchestrator with low added latency.

## Tasks

- [ ] On `CMD_MIDI_SEND`, queue the byte for the TCP socket instead of echoing it into the IN queue
- [ ] Forward bytes verbatim — no MIDI parsing/filtering/framing (D-02)
- [ ] Flush promptly (small coalescing window) to stay within the latency budget (C-01)
- [ ] Handle partial sends / lwIP backpressure without losing bytes

## Acceptance

Bytes the ST emits via `Bconout(3)` appear at the orchestrator (or echo peer) in
order; measured added latency is within target (set in EPIC-05).

## Notes

`CMD_MIDI_SEND` is the exact echo seam from EPIC-02 STORY-03. The stream is opaque
bytes (D-02) — never reorder or drop. MIDI Maze is latency-sensitive (C-01):
coalesce only within a few ms.
