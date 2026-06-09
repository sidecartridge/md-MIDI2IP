---
id: STORY-01
epic: EPIC-02
title: Define the OUT/IN MIDI ring buffers in the shared region
status: todo
milestone: alpha-mvp
---

## Goal

Reserve and document two byte rings — OUT (Atari → RP) and IN (RP → Atari) — plus
their head/tail indices in the `APP_FREE` arena, as symbolic offsets shared by
both targets.

## Tasks

- [ ] Choose ring sizes (power-of-two) balancing burst tolerance against added latency (C-01)
- [ ] Add offset/size constants to `rp/src/include/chandler.h`
- [ ] Mirror the same offsets as `equ`s in `target/atarist/src/main.s` (and reference them from `userfw.s`)
- [ ] Document the layout in this folder and in `programming.md`'s region table

## Acceptance

Both builds compile referencing only the named symbols; a value written at each
ring offset reads back identically from the opposite side.

## Notes

Single-producer/single-consumer per ring → no locks if each index is owned by one
side (OUT: m68k writes head, RP reads tail; IN: RP writes head, m68k reads tail).
Mirror the advance-first convention already used for the `Iorec` buffer.
