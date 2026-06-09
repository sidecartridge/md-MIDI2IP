---
id: EPIC-01
title: m68k BIOS/XBIOS MIDI call hooking
status: todo
---

## Goal

Intercept the Atari ST OS calls that move MIDI bytes so traffic can be diverted
to the cartridge (and from there to the network) instead of only the physical
MIDI ACIA. This is the foundation everything else builds on.

## Scope

- In scope: installing/chaining the BIOS (`trap #13`) and XBIOS (`trap #14`)
  vectors, filtering for the MIDI device (BIOS device 3) and XBIOS `Midiws`,
  and handing bytes to/from the shared region.
- Out of scope: the transport ring buffers (EPIC-02) and networking (EPIC-03).
  This epic only captures/injects bytes at the OS boundary. The exception is
  STORY-05's test-only RP loopback (OUT→IN echo), a validation scaffold that the
  real transport later replaces.

## Assumptions & risks

- **Target is MIDI Maze** (D-01), which does MIDI I/O through the OS calls — so
  hooking BIOS/XBIOS captures it. Apps that drive the 6850 MIDI ACIA registers
  directly and run their own MIDI interrupt handler are **out of scope**: those
  I/O cycles never reach the cartridge, so this approach can't intercept them.
- **MIDI Maze's call paths (D-05, from the disassembly + thesis §2.4.2):** it uses
  **both BIOS and XBIOS**. Output = BIOS `Bconout(3)` (`trap #13`). Input = BIOS
  `Bconstat(3)`/`Bconin(3)` polling in the game loop **plus** an **XBIOS `trap #14`
  MIDI-IN read after every write** (via wrappers `$188f0`→`$341a2`) — the ring
  readback that drives master election and per-frame sync. So we **must hook both
  trap #13 and trap #14**, and the XBIOS read is MVP-critical, not optional
  (un-serviced, MIDI Maze's send routines abort). The exact XBIOS fn# for the
  readback is unconfirmed in the source — likely `Iorec(2)`; pin it down during
  bring-up. (`Midiws` is not used; STORY-02 stays generality-only.)
- **Code-budget risk:** the hooks + ring helpers (EPIC-02) + dispatch share the
  6 KB `userfw` budget; the STORY-05 self-test adds to it (test build only).

## Stories

- STORY-01 — Install and chain BIOS/XBIOS trap vectors safely
- STORY-02 — Hook XBIOS Midiws (MIDI output)
- STORY-03 — Hook BIOS Bconout/Bcostat device 3 (MIDI output)
- STORY-04 — Hook BIOS Bconin/Bconstat device 3 (MIDI input)
- STORY-05 — Automated MIDI hook validation harness (capstone)

## Notes

The hooking logic lives in `target/atarist/src/userfw.s` (currently the Cconws
stub). Preserve the original vectors and restore them on reset so a crash can't
leave the machine pointing at unmapped cartridge code.
