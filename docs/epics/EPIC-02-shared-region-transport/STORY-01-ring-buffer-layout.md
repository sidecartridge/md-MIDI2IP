---
id: STORY-01
epic: EPIC-02
title: Define MIDI IN/OUT ring buffers in the shared region
status: todo
milestone: alpha-mvp
---

## Goal

Reserve and document two byte rings (Atari→net OUT, net→Atari IN) plus their
head/tail indices in the `APP_FREE` arena, as symbolic offsets shared by both
targets.

## Tasks

- [ ] Choose ring sizes (power-of-two) balancing burst tolerance against added latency (C-01)
- [ ] Add offset/size constants to `rp/src/include/chandler.h`
- [ ] Mirror the same offsets as `equ`s in `target/atarist/src/main.s`
- [ ] Document the layout in this folder and in `programming.md`'s region table

## Acceptance

Both builds compile referencing only the named symbols; a written test value at
each ring offset reads back identically from the opposite side.

## Notes

Single-producer/single-consumer per ring → no locks needed if head/tail are
updated by exactly one side each.
