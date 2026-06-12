---
id: STORY-01
epic: EPIC-06
title: Per-app config keys for the MIDI endpoint
status: done
milestone: alpha-mvp
---

## Goal

Define and persist the settings MIDI-to-IP needs, readable at startup and
editable at runtime.

## Tasks

- [x] Add keys: `MIDI_HOST`, `MIDI_PORT`, `MIDI_ENABLED` (transport fixed to TCP per D-03; physical-port passthrough deferred per D-07)
- [x] Provide sensible defaults in `aconfig` init (host `0.0.0.0`, port `5005`, enabled `true`)
- [x] Load on startup and apply (`midi_init` reads them; `midi_net_poll` gates the connection on `MIDI_ENABLED`)
- [x] Persist to `CONFIG_FLASH`: `aconfig_init` writes the defaults; `settings_save` (Core0-safe) persists edits (the edit UI is STORY-04)

## Acceptance

Settings survive a power cycle; changing the endpoint and re-enabling connects to
the new host without a rebuild.

## Notes

Keys live in `aconfig.c`'s `defaultEntries[]` (names/defaults in `midi.h`); read
in `midi.c::midi_init` into `midiNetHost` / `midiNetPort` / `midiEnabled`. Respect
`PICO_FLASH_ASSUME_CORE0_SAFE=1`. The runtime change-and-reconnect path is exercised
once STORY-04 adds the on-screen editor. Builds green; power-cycle persistence to
be confirmed on hardware.
