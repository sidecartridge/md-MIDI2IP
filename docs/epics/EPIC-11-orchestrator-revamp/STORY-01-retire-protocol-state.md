---
id: STORY-01
epic: EPIC-11
title: Retire the protocol-state model — dumb relay, keep --inspect
status: done
---

## Goal

Remove the EPIC-08 `RingState` protocol-state model (master-election heuristic, phase
tracking, COUNT) now that the firmware drives the ring itself. The orchestrator goes
back to relaying raw bytes; the read-only `MidiMazeInspector` behind `--inspect` stays
for debugging, fully off the relay path.

## Tasks

- [x] Remove the `RingState` class and its per-player decoder map from the relay/registry path
- [x] Drop any coordination flag/state (`--coordinate`, master/COUNT tracking) from the CLI + serve loop; keep the dumb single-global-ring relay
- [x] Keep `MidiMazeInspector` + `--inspect` intact and independent — it decodes/logs but never feeds back into relaying
- [x] Excise the `RingState`-derived fields from `_status_snapshot` (replaced by per-node telemetry in STORY-04)
- [x] Confirm `selftest.py` passes and a 2-node session still relays byte-exact

## Acceptance

The orchestrator is a pure byte relay — no protocol state influences relaying.
`--inspect` still decodes a live session to the log. Self-test green; a 2-node relay is
byte-exact.

## Notes

`RingState` was a heuristic (it caused the D-04 master-flip on hardware); with the
firmware owning the ring it is dead weight. `--inspect` is the keeper: read-only,
opt-in, off the hot path (D-02 — the relay stays opaque).
