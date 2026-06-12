---
id: STORY-01
epic: EPIC-08
title: Ring protocol-state model (stateful, authoritative)
status: done
milestone: alpha-mvp
---

## Goal

Promote the read-only `--inspect` decoder (`MidiMazeInspector`) into a **stateful
per-ring model** the coordinator can act on: who is the MASTER, what phase the
ring is in, and how many players the last COUNT-PLAYERS saw. All of this is
derived purely from observed bytes (D-02 stays true for the *transport*; only the
orchestrator interprets). This is the read-only foundation; STORY-02/03 act on it.

## Tasks

- [x] `RingState` tracks the ring **phase** (idle / electing / counting / name-dialog / in-game / terminated) and the **master** (others are slaves by implication) from the decoded stream
- [x] **Master detection** (heuristic: first originator of a post-election control msg; STORY-02 makes it authoritative): `master` / `phase` / `last_count` surfaced in `status.json` + the HTML status
- [x] **Reset on membership change** (`add_player`/`remove_player` → `_reset_round`): the ring must re-stabilise before a game (D-04)
- [x] Unit-tested from recorded byte sequences (election → count → start-game → terminate → join-reset) in `selftest.py` Phase C, no hardware

## Acceptance

The orchestrator status shows, per ring, the current master, phase, and last
player count, computed only from observed bytes; the model resets cleanly on any
join/leave.

## Notes

Builds directly on the in-line `MidiMazeInspector` in `orchestrator.py`. The
decoder is best-effort/per-stream today; this makes it ring-aware and
authoritative. Keep it read-only here. Acting on it is STORY-02. The hardware
traces (election storm; `COUNT-PLAYERS` interrupted by stray `0x00`) are the
test fixtures.
