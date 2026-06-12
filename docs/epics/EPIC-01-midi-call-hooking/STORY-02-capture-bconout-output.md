---
id: STORY-02
epic: EPIC-01
title: Capture MIDI output (BIOS Bconout, device 3)
status: done
milestone: alpha-mvp
---

## Goal

From the BIOS (`trap #13`) hook, intercept `Bconout` with device 3 (MIDI) and
read the byte MIDI Maze is sending, so it can be fed into the local loopback
(STORY-04) and later the OUT ring (EPIC-02).

## Tasks

- [x] Arg-access prologue: handle user/supervisor caller and the 68010+ long frame so `6(a0)`=function, `8(a0)`=device, `11(a0)`=byte
- [x] Detect `Bconout` (function 3) with device == 3
- [x] Read the output byte from the trap frame
- [x] Chain non-matching calls through untouched (other functions, device 2 console/keyboard/screen, all non-MIDI)

## Acceptance

A MIDI byte written by `Bconout(3)` is read correctly by the hook; everything
else (screen, keyboard) behaves identically. Confirmed on hardware: the first
captured byte was `0x00`, MIDI Maze's master-election request.

## Notes

The arg-access prologue is the md-drives-emulator pattern. Device 2 (served by
the same BIOS wrapper) carries console/keyboard/screen and must pass through.
`Bcostat` back-pressure isn't needed for the local loopback (no ring to fill);
it lands in EPIC-02 when the OUT ring can back up.
