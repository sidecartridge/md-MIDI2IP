---
id: EPIC-01
iteration: 1
title: m68k MIDI hooking + local loopback
status: done
---

## Goal

Intercept the Atari ST OS calls MIDI Maze uses for MIDI I/O and wire a
**local loopback** so a single ST plays MIDI Maze solo (a "ring of one") with
**no MIDI cable, no second ST, no RP transport, and no network**. This proves
the whole m68k path (hook → capture output → inject input) end to end. It is
a self-contained, demonstrable milestone. Later epics move the loopback outward:
EPIC-02 routes it through the RP via shared-region rings; EPIC-03 routes it over the
network to the orchestrator.

## Scope

- In scope (all m68k-side): installing/chaining the BIOS (`trap #13`) device-3
  vector via XBRA, capturing `Bconout(3)` output, serving `Bconin(3)`/`Bconstat(3)`
  input, and echoing output→input locally.
- Out of scope: the shared-region rings and RP transport (EPIC-02) and the
  network (EPIC-03). EPIC-01 keeps everything on the Atari; nothing crosses to
  the RP except the one-time install handshake.

## Assumptions & risks

- **MIDI Maze's call paths are confirmed** (D-05, on hardware): output via BIOS
  `Bconout(3)`; input read via BIOS `Bconin(3)`/`Bconstat(3)` (device 3). `Midiws`
  and the XBIOS/`Iorec` path are **not** used, so they're out of scope.
- **Code-budget:** the hooks + loopback share the 6 KB `userfw` budget; current
  build is well under the 8 KB cartridge cap.

## Stories

- STORY-01: Install and chain the BIOS (trap #13) device-3 vector safely (XBRA)
- STORY-02: Capture MIDI output (BIOS Bconout, device 3)
- STORY-03: Deliver MIDI input to Bconin(3)/Bconstat(3)
- STORY-04: Local loopback: solo MIDI Maze (ring of one)

## Notes

Implemented in `target/atarist/src/userfw.s` with a one-time RP handshake
(`rp/src/midi.c`) that patches the saved BIOS vector into the served ROM image.
Confirmed on hardware: boots to GEM (non-MIDI undisturbed), and MIDI Maze becomes
MASTER on a single machine.

**Evolution note:** EPIC-01 originally also hooked XBIOS (`trap #14`) and injected
received bytes into the system `Iorec(2)` buffer. That was later simplified. The
BIOS hook now *is* the MIDI device, serving `Bconin`/`Bconstat` directly from the
RP queue with **no XBIOS vector and no Iorec** (D-05). Some story bodies below
still describe that original approach.
