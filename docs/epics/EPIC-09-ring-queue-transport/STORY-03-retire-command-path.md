---
id: STORY-03
epic: EPIC-09
title: Retire the per-byte CMD_MIDI_SEND / CMD_MIDI_RECV command path
status: todo
---

## Goal

Once both directions stream over commemul (STORY-01/02), remove the now-dead per-byte
command path — the `CMD_MIDI_SEND`/`CMD_MIDI_RECV` handlers on the RP and the
`send_sync` MIDI calls on the m68k — so the only MIDI transport is the fast path.

## Tasks

- [ ] Remove the `CMD_MIDI_SEND` / `CMD_MIDI_RECV` cases from `midi.c` (and the command IDs if unused elsewhere)
- [ ] Remove the `send_sync_command_to_sidecart` MIDI usage from `userfw.s` (keep the routine only if the config/menu path still needs it)
- [ ] Drop any now-unused shared offsets / constants tied to the old per-byte protocol
- [ ] Confirm both builds stay green and the 8 KB cartridge-code budget is unaffected

## Acceptance

No per-byte MIDI command remains; the MIDI path is exclusively the commemul byte
stream (OUT) + RP-owned ring (IN). Both targets build.

## Notes

Pure cleanup, gated on STORY-01/02 working on hardware. Verify call sites before
deleting — the TPROTOCOL command channel itself stays for config/menu.
