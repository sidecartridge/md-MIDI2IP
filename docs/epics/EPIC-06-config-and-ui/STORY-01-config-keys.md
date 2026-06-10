---
id: STORY-01
epic: EPIC-06
title: Per-app config keys for the MIDI endpoint
status: todo
milestone: alpha-mvp
---

## Goal

Define and persist the settings MIDI-to-IP needs, readable at startup and
editable at runtime.

## Tasks

- [ ] Add keys: endpoint host, port, transport, enabled (physical-port passthrough deferred — D-07)
- [ ] Provide sensible defaults in `aconfig` init
- [ ] Load on startup and apply (gate networking on `enabled`)
- [ ] Persist changes to `CONFIG_FLASH` (Core0-safe flash write)

## Acceptance

Settings survive a power cycle; changing the endpoint and re-enabling connects to
the new host without a rebuild.

## Notes

Keys live in `aconfig.c`. Respect `PICO_FLASH_ASSUME_CORE0_SAFE=1`.
