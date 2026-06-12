---
id: STORY-04
epic: EPIC-01
title: Local loopback: solo MIDI Maze (ring of one)
status: done
milestone: alpha-mvp
---

## Goal

Wire the capture (STORY-02) to the injection (STORY-03) so the ST receives its
own MIDI output (a "ring of one"). MIDI Maze sends `0x00`, reads its own `0x00`
back, becomes MASTER, and is then playable solo against drones on a single machine
with **no MIDI cable and no second ST**. This is the self-contained EPIC-01
deliverable; it proves the whole m68k hook → capture → inject → read path that
EPIC-02/03 later route through the RP and the network.

## Tasks

- [x] In the `Bconout(3)` hook, echo each captured byte back to the ST's MIDI input, then chain so Bconout still returns normally
- [x] Confirm master election: the ST receives its own `0x00` and becomes MASTER
- [x] Confirm non-MIDI I/O is undisturbed (boots to GEM, keyboard/screen normal, no instability)
- [x] Confirm MIDI Maze reaches MASTER + the config screen via the loopback

## Acceptance

On a single ST with the cartridge and no peers, MIDI Maze becomes MASTER and
reaches the config screen, proving the local loopback delivers its own MIDI back.
Confirmed on hardware. (It does **not** start a match: MIDI Maze waits for a
SLAVE; that needs a 2nd node, D-09 / EPIC-03.)

## Notes

Pure m68k: the echo never touches the RP, so there's no per-byte RP traffic
(the serial console is silent during play; only the one-time install handshake
logs). EPIC-02 replaces this local echo with an RP-side echo over shared-region
rings; EPIC-03 replaces the RP echo with the network round-trip.
