---
id: STORY-03
epic: EPIC-08
title: Ring flow-control — survive the ~4 KB SEND-DATA without loss
status: done
milestone: alpha-mvp
---

## Goal

Carry the **~4 KB `SEND-DATA` (`0x83`)** — the 64×64 maze + game options the
MASTER broadcasts at START-GAME — around the full ring **byte-exact**. Today
(D-11) it overflows the RP's IN path (1 KB queue / 256 B `MIDI_IN_BUFFER` per
`CMD_MIDI_RECV`) when the maze circulates back, dropping
bytes exactly at "start game" so the maze never loads.

## Tasks

- [x] **Locate the loss**: confirm where the 4 KB burst is dropped (RP IN queue, or the 256 B shared-buffer cadence) via `--inspect` + serial trace
- [x] **RP-side**: size/flow-control the IN path so a 4 KB+ burst is delivered loss-free — pace delivery (via `Bconin`) to what MIDI Maze consumes, **never drop** (back-pressure). Cross-refs EPIC-02 ring sizing, C-01
- [x] **Orchestrator-side (optional)**: pace/chunk large relayed messages so a slow IN consumer isn't flooded (byte-agnostic — D-02 holds)
- [x] **Verify** byte-exact delivery of a ≥4 KB message end-to-end (no loss / dup / reorder), e.g. a CRC over the relayed SEND-DATA

## Acceptance

A ≥4 KB SEND-DATA travels the full ring (ST ↔ Hatari) byte-exact and the maze
loads on the receiving node; no overflow drops under burst.

## Notes

Touches RP firmware (the EPIC-02/03 IN buffers) **and** optionally the
orchestrator. Pacing/sizing is byte-agnostic, so D-02 (no MIDI parsing) still
holds for the transport. The MVP ring is 2 players; sizing should still bound the
worst case (the maze passes every hop).
