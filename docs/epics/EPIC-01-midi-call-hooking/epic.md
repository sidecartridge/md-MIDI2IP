---
id: EPIC-01
title: m68k MIDI hooking + local loopback
status: done
---

## Goal

Intercept the Atari ST OS calls MIDI Maze uses for MIDI I/O and wire a
**local loopback** so a single ST plays MIDI Maze solo (a "ring of one") with
**no MIDI cable, no second ST, no RP transport, and no network**. This proves
the whole m68k path — hook → capture output → inject input — end to end, and is
a self-contained, demonstrable milestone. Later epics move the loopback outward:
EPIC-02 routes it through the RP via shared-region rings, EPIC-03 over the
network to the orchestrator.

## Scope

- In scope (all m68k-side): installing/chaining the BIOS (`trap #13`) and XBIOS
  (`trap #14`) vectors via XBRA, capturing `Bconout(3)` output, injecting into
  the `Iorec(2)` MIDI input buffer, and echoing output→input locally.
- Out of scope: the shared-region rings and RP transport (EPIC-02) and the
  network (EPIC-03). EPIC-01 keeps everything on the Atari; nothing crosses to
  the RP except the one-time install handshake.

## Assumptions & risks

- **MIDI Maze's call paths are confirmed** (D-05, on hardware): output via BIOS
  `Bconout(3)`; input read from the system MIDI `Iorec(2)` buffer (which both
  `Bconin(3)` and the XBIOS readback consume). `Midiws` is **not** used, so it's
  out of scope.
- **Code-budget:** the hooks + loopback share the 6 KB `userfw` budget; current
  build is well under the 8 KB cartridge cap.

## Stories

- STORY-01 — Install and chain BIOS/XBIOS trap vectors safely (XBRA)
- STORY-02 — Capture MIDI output (BIOS Bconout, device 3)
- STORY-03 — Inject MIDI input (the Iorec(2) buffer)
- STORY-04 — Local loopback: solo MIDI Maze (ring of one)

## Notes

Implemented in `target/atarist/src/userfw.s` with a one-time RP handshake
(`rp/src/midi.c`) that patches the saved vectors / Iorec pointer into the served
ROM image. Confirmed on hardware: boots to GEM (non-MIDI undisturbed), and MIDI
Maze becomes MASTER on a single machine.
