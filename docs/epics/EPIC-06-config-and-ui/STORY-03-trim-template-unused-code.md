---
id: STORY-03
epic: EPIC-06
title: Trim the microfirmware template of unused code
status: in-progress
---

## Goal

MIDI-to-IP started from the Sidecartridge app template, which ships subsystems
this app doesn't use. Remove the dead weight so the codebase reflects only what
MIDI-to-IP needs — smaller, clearer, and easier to reason about.

## Tasks

- [ ] Inventory template/demo code not used by MIDI-to-IP (e.g. the Cconws demo in `userfw.s`, ROM-loading scratch, firmware-download path, unused terminal/sample commands)
- [x] **Remove the SD-card subsystem** — `sdcard.c`, `hw_config.c`, the bundled FatFs / `ff/ffconf.h` config and their CMake wiring — MIDI-to-IP never touches the SD card
- [ ] Confirm each remaining candidate is truly unused before removing (grep call sites). Must-keep: `network.c` + `gconfig` Wi-Fi, chandler, display, config. Likely-safe cut: `download.c` (firmware download)
- [ ] Remove the dead code and its build wiring (CMake/Makefile/linker), keeping both builds green
- [ ] Drop now-unused config keys and shared-region fields
- [ ] Verify the UF2 still builds and boots on hardware; record the size reduction

## Acceptance

Both targets build, the UF2 boots and runs the MIDI path on hardware, no
template/demo strings remain, and the dist UF2 is no larger than before (ideally
smaller). Nothing MIDI-to-IP relies on was removed.

## Notes

Per the repo guardrails, deletions must be deliberate — this story is the
explicit authorization to remove template dead code, but verify each removal
against actual call sites first. Do this after the MIDI path works, so "unused"
is unambiguous.
