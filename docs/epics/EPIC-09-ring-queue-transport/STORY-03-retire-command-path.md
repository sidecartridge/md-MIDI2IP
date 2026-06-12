---
id: STORY-03
epic: EPIC-09
title: Retire the per-byte CMD_MIDI_SEND / CMD_MIDI_RECV command path
status: done
---

## Goal

Once both directions stream over commemul (STORY-01/02), remove the now-dead per-byte
command path (the `CMD_MIDI_SEND`/`CMD_MIDI_RECV` handlers on the RP and the
`send_sync` MIDI calls on the m68k) so the only MIDI transport is the fast path.

## Tasks

- [x] Remove the `CMD_MIDI_SEND` / `CMD_MIDI_RECV` cases from `midi.c` and the command IDs (midi.h); the m68k handlers were already the fast path, and the defines/equs are gone.
- [x] Remove the `send_sync_command_to_sidecart` MIDI usage from `userfw.s`; OUT/IN are bit-8/bit-9 `tst.b`, and `send_sync` is kept only for the boot-time save-vector (config-phase).
- [x] Drop the now-unused constants (the `CMD_MIDI_SEND`/`CMD_MIDI_RECV` equs in userfw.s + defines in midi.h) and refresh the stale hook/comment text.
- [x] Confirm both builds stay green and the 8 KB cartridge-code budget is unaffected: cartridge code 2276/8192 B.

## Acceptance

No per-byte MIDI command remains; the MIDI path is exclusively the commemul byte
stream (OUT) + RP-owned ring (IN). Both targets build. **Met.**

## Notes

Pure cleanup, gated on STORY-01/02 working on hardware. `CMD_MIDI_SAVE_VECTOR` (the
boot install) and the TPROTOCOL command channel (config/menu) stay. Only the per-byte
OUT/IN commands were retired.
