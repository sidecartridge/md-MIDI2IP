---
id: STORY-01
epic: EPIC-02
title: Define the byte-pipe protocol + shared IN buffer
status: done
milestone: alpha-mvp
---

## Goal

Define the dumb byte-pipe protocol both sides agree on: the two commands
(`CMD_MIDI_SEND` m68k→RP, `CMD_MIDI_RECV` request for IN bytes) and the shared
**IN buffer** the RP writes and the m68k reads (a count field plus a byte buffer,
modeled on GEMDRIVE's `READ_BYTES` / `READ_BUFFER`). Raw bytes only; no MIDI
semantics.

## Tasks

- [x] Define `CMD_MIDI_SEND` (`$0301`) / `CMD_MIDI_RECV` (`$0302`) in `rp/src/include/midi.h` and mirror them in `userfw.s`
- [x] Define the shared IN buffer layout in `APP_FREE` (`$FA2300`): `MIDI_IN_COUNT` (longword) + `MIDI_IN_BUFFER` (256 B); offsets in midi.h, addresses in userfw.s
- [x] RP zeroes `MIDI_IN_COUNT` at init in `midi_init()` (after the firmware image is copied to RAM)
- [x] Document the layout (midi.h / userfw.s constants, cross-referenced)

## Acceptance

Both targets build referencing only the named symbols; the RP-written
`MIDI_IN_COUNT` reads back on the m68k at the agreed offset. (The real send/recv
logic is STORY-02/03.)

**Verified on hardware:** a throwaway probe seeded `MIDI_IN_COUNT` with
`0x12345678`; the m68k read `$FA2300` and reported it back exactly, confirming
the offset *and* the word-swap end to end. Probe removed afterward.

## Notes

The m68k owns no shared state: the RP writes `MIDI_IN_COUNT`/`MIDI_IN_BUFFER`
and the m68k reads them. OUT bytes ride the command itself (ROM3 addressing), so they
need no shared buffer. Keep the IN buffer small; MIDI Maze's bytes are tiny
versus GEMDRIVE's 4 KB file reads.
