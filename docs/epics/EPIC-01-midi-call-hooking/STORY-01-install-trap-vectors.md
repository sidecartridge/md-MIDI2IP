---
id: STORY-01
epic: EPIC-01
title: Install and chain BIOS/XBIOS trap vectors safely
status: todo
milestone: alpha-mvp
---

## Goal

From `userfw.s`, replace the `trap #13` (BIOS) and `trap #14` (XBIOS) vectors
with our handlers that inspect the call and chain through to the original OS
routine for everything we don't care about.

## Tasks

- [ ] Save the original BIOS/XBIOS vector addresses (Supexec / supervisor mode)
- [ ] Install our trap handlers and chain unmatched calls to the originals
- [ ] Restore original vectors on cartridge reset / RESET command
- [ ] Confirm non-MIDI BIOS/XBIOS calls behave identically (boot to desktop)

## Acceptance

Machine boots to GEM normally with hooks installed; removing/disabling the app
restores stock behaviour; no crash on warm reset.

## Notes

Vector table: BIOS = `$B4` is the trap #13 handler? Verify exact vector
addresses against TOS docs before coding. Use supervisor mode to patch.

Filter strictly: act only on **device 3** (MIDI). The same BIOS wrapper serves
device 2 (console/keyboard/screen — MIDI Maze's "Lee de teclado"/"Escribe por
pantalla" calls); those, and all non-MIDI BIOS/XBIOS traffic, must chain through
untouched so keyboard and screen I/O are undisturbed.
