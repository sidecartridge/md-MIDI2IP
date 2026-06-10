---
id: STORY-01
epic: EPIC-08
title: Ring protocol-state model (stateful, authoritative)
status: todo
milestone: alpha-mvp
---

## Goal

Promote the read-only `--inspect` decoder (`MidiMazeInspector`) into a **stateful
per-ring model** the coordinator can act on: who is the MASTER, what phase the
ring is in, and how many players the last COUNT-PLAYERS saw — derived purely from
observed bytes (D-02 stays true for the *transport*; only the orchestrator
interprets). This is the read-only foundation; STORY-02/03 act on it.

## Tasks

- [ ] Per-player role (unknown / master / slave) + ring **phase** (electing / counting / name-dialog / in-game / terminated) tracked from the decoded stream
- [ ] **Master detection**: the node whose `0x00` returns around the ring (and/or originates `0x80`/`0x84`); surface master + phase + last player-count in the HTTP status
- [ ] **Reset on membership change** (join/leave) — the ring must re-stabilise before a game (D-04)
- [ ] Unit-test the model from recorded byte sequences (election, count, start-game, terminate) — no hardware

## Acceptance

The orchestrator status shows, per ring, the current master, phase, and last
player count, computed only from observed bytes; the model resets cleanly on any
join/leave.

## Notes

Builds directly on the in-line `MidiMazeInspector` in `orchestrator.py`. The
decoder is best-effort/per-stream today; this makes it ring-aware and
authoritative. Keep it read-only here — acting on it is STORY-02. The hardware
traces (election storm; `COUNT-PLAYERS` interrupted by stray `0x00`) are the
test fixtures.
