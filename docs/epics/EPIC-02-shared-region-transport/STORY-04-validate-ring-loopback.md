---
id: STORY-04
epic: EPIC-02
title: Validate — solo MIDI Maze via the RP-mediated rings
status: todo
milestone: alpha-mvp
---

## Goal

Confirm the loopback now runs through the shared-region rings and the RP echo
(not the m68k-local path), with the same playable result, and measure what the
extra hop costs.

## Tasks

- [ ] Solo MIDI Maze becomes MASTER and plays via the rings + RP echo (parity with the EPIC-01 local loopback)
- [ ] Exercise ring wrap and full/empty conditions; assert ordering and zero byte loss
- [ ] Compare per-hop latency against the EPIC-01 local loopback (feeds C-01 / EPIC-05 STORY-02)
- [ ] Serial console shows the RP echo active (OUT drained / IN filled counts)

## Acceptance

The RP-mediated loopback is at parity with EPIC-01's local one — MIDI Maze plays
solo — and the rings handle saturation without loss or lockup. Added latency is
recorded.

## Notes

Parity with EPIC-01 (same observable game) is the bar; the difference is *where*
the echo lives. Once this passes, EPIC-03 replaces the RP echo with the network
round-trip to the orchestrator.
