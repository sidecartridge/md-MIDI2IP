---
id: STORY-01
epic: EPIC-01
title: Install and chain the BIOS (trap #13) device-3 vector safely
status: done
milestone: alpha-mvp
---

> **Superseded:** this story originally also installed the XBIOS (`trap #14`)
> vector. That hook was later removed; only the BIOS device-3 vector is hooked
> now (D-05). The body below is the original record.

## Goal

From `userfw.s`, replace the `trap #13` (BIOS) and `trap #14` (XBIOS) vectors
with our handlers that inspect the call and chain through to the original OS
routine for everything we don't care about.

## Tasks

- [x] Save the original BIOS/XBIOS vector addresses (Supexec / supervisor mode)
- [x] Install our trap handlers and chain unmatched calls to the originals
- [x] Restore original vectors on cartridge reset / RESET command
- [x] Confirm non-MIDI BIOS/XBIOS calls behave identically (boot to desktop)

## Acceptance

Machine boots to GEM normally with hooks installed; removing/disabling the app
restores stock behaviour; no crash on warm reset.

## Notes

Vector table: BIOS = `$B4` is the trap #13 handler? Verify exact vector
addresses against TOS docs before coding. Use supervisor mode to patch.

Filter strictly: act only on **device 3** (MIDI). The same BIOS wrapper serves
device 2 (console/keyboard/screen, i.e. MIDI Maze's "Lee de teclado"/"Escribe por
pantalla" calls); those and all non-MIDI BIOS/XBIOS traffic must chain through
untouched so keyboard and screen I/O are undisturbed.

### Done (hardware-verified)

Implemented with the **XBRA** convention (cookie `'SDMI'`), matching
md-drives-emulator: BIOS installed via `Setexc($2D)`, XBIOS via direct `$B8`
poke; the original vectors live in each handler's XBRA `<old>` field, which the
RP patches into the served ROM image (`CMD_MIDI_SAVE_VECTOR` → `rp/src/midi.c`).
Verified on real hardware: boots to the GEM desktop with keyboard/screen normal (non-MIDI
chaining is transparent) and no instability. A warm reset rebuilds the OS vectors.
A follow-on cable-free **loopback** (echo `Bconout(3)` into the
`Iorec(2)` MIDI input buffer) then let MIDI Maze become MASTER on a single
machine, confirming the full hook → capture → inject → read path and the D-05
input route.
