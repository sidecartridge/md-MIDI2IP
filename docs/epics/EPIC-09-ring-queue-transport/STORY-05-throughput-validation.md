---
id: STORY-05
epic: EPIC-09
title: On-hardware throughput + duplicate-race validation
status: todo
---

## Goal

Prove on real hardware that the new transport clears the D-12 ceiling and that
decision A holds — the fire-and-forget IN path never duplicates a byte.

## Tasks

- [ ] Re-run the per-direction byte/sec instrumentation; confirm OUT and IN both exceed the 31250-baud wire rate (~3125 B/s) with margin
- [ ] Instrument for duplicate / dropped IN bytes (the decision-A race) over a sustained burst; confirm none
- [ ] Smoke-test a 2-node MIDI Maze (physical ST + orchestrator, second node in Hatari): master/slave, names, and the SEND-DATA maze transfer
- [ ] If duplicates ever appear, document falling back to the 1-word m68k cursor

## Acceptance

Measured throughput beats real MIDI wire speed in both directions, no duplicate/lost
IN bytes under burst, and a 2-node game completes the maze handshake — closing D-12.

## Notes

Overlaps EPIC-10 (full hardware validation II); this story is the transport-specific
gate. Replaces the Iteration-1 ~970 B/s measurement.
