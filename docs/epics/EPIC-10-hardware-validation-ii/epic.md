---
id: EPIC-10
iteration: 2
title: Hardware validation II
status: done
---

## Goal

Re-validate the full stack on **real hardware** once the EPIC-09 ring-queue
transport lands: a full 2-player MIDI Maze match on the RP-hardware path, and the
automated regression gate over the whole ST → RP → network → orchestrator path.
Both were proven impossible in Iteration 1 not for protocol reasons but because of
the per-byte throughput ceiling (**D-12**), so they were deferred here, gated on
EPIC-09.

## Scope

- **In:** validate a full 2-player match on the RP-hardware path (the deferred
  EPIC-08 STORY-04); the cartridge-resident self-test exerciser + serial verdict
  as an automated regression gate (the deferred EPIC-07 STORY-02).
- **Out:** the transport rework itself (EPIC-09); the Hatari-gateway match, which
  is **already validated** in Iteration 1 (EPIC-05 STORY-04) since that peer is
  pure software and never hit D-12.

## Stories

- STORY-01: Automated regression gate (self-test over the full stack) (_moved from EPIC-07_)
- STORY-02: Validate: a full 2-player MIDI Maze match starts and plays (_moved from EPIC-08_)

## Notes

Continuation of EPIC-07 (Hardware validation) for Iteration 2: it carries the two
validation stories that could only run after the D-12 transport fix. Blocked on
EPIC-09. There is no point validating or gating a hardware match until it can
sustain lock-step (C-01). References: D-12 (the ceiling), EPIC-09 (the fix),
EPIC-05 STORY-04 (the software-peer match, already done).
