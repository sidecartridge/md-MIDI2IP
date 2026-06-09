---
id: STORY-04
epic: EPIC-02
title: Validate — solo MIDI Maze over the byte pipe
status: todo
milestone: alpha-mvp
---

## Goal

Confirm the loopback now runs through the RP byte pipe (not the m68k-local echo),
with the same playable result, and measure what the round-trip costs.

## Tasks

- [ ] Solo MIDI Maze becomes MASTER and plays via `CMD_MIDI_SEND`/`CMD_MIDI_RECV` + the RP echo (parity with EPIC-01)
- [ ] Byte-exact, in-order delivery; no loss when the IN buffer fills
- [ ] Compare per-byte round-trip latency against the EPIC-01 local loopback (feeds C-01 / EPIC-05 STORY-02)
- [ ] Serial console shows the pipe active (SEND / RECV counts)

## Acceptance

The byte-pipe loopback is at parity with EPIC-01's local one — MIDI Maze plays
solo — with no loss or lockup, and the added latency is recorded.

## Notes

Parity with EPIC-01 (same observable game) is the bar; the difference is *where*
the echo lives. Once this passes, EPIC-03 replaces the RP echo with the network
round-trip to the orchestrator.
