---
id: STORY-05
epic: EPIC-09
title: On-hardware throughput + duplicate-race validation
status: done
---

## Goal

Prove on real hardware that the new transport clears the D-12 ceiling and resolve the
fire-and-forget IN-path duplicate question.

## Tasks

- [x] Re-run the per-direction byte/sec instrumentation; OUT and IN both clear the wire rate with margin (hundreds of B/s sustained, `cap/s` into the hundreds, vs. the ~970 B/s D-12 ceiling)
- [x] Instrument for duplicate / dropped IN bytes — **duplicates DID occur** (`IN_adv` ≈ 13× `RX`): decision A's no-race premise was false
- [x] Smoke-test a 2-node MIDI Maze (physical ST + orchestrator, second node): master/slave, names, SEND-DATA maze transfer — **playable**
- [x] Document the fallback: realised as the `MIDI_IN_ACK` confirm handshake (STORY-02), not the 1-word cursor

## Acceptance

Measured throughput beats real MIDI wire speed in both directions, no duplicate/lost
bytes under burst, and a 2-node game completes — closing D-12. **Met:** game is
playable end-to-end once both the IN duplicate-read (advance-ack) and the OUT burst
drop (OUT ring) were fixed.

## Notes

Overlaps EPIC-10 (full hardware validation II); this story is the transport-specific
gate. Replaces the Iteration-1 ~970 B/s measurement. Key finding: the decision-A race
was real on hardware and required the confirm-ack — recorded in STORY-02. Two
distinct losses had to be closed for playability: IN re-reads (`IN_adv >> RX`) and OUT
drops (`OUT > RX`).
