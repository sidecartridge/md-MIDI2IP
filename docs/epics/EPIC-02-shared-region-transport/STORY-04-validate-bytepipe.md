---
id: STORY-04
epic: EPIC-02
title: Validate: MIDI Maze handshake over the byte pipe
status: done
milestone: alpha-mvp
---

## Goal

Confirm MIDI Maze runs through the RP byte pipe (not the m68k-local echo) as far
as a single node can be taken, covering master election and the COUNT-PLAYERS / config
handshake, to prove the transport carries the game's bytes faithfully.

## Tasks

- [x] MIDI Maze becomes MASTER via `CMD_MIDI_SEND`/`CMD_MIDI_RECV` + the RP echo (parity with EPIC-01)
- [x] The protocol round-trips: master `0x00`, `0x80` COUNT-PLAYERS, and the config screen all flow through the pipe correctly
- [x] Servicing input on every device-3 call (not just `Bconout`) so read-wait loops are fed (no background loop exists during gameplay)
- [x] Console no longer flooded by MIDI traffic (terminal logs only its own namespace)

## Acceptance

On a single ST, MIDI Maze reaches MASTER and the config screen with the bytes
proven to round-trip m68k → RP → m68k. **Verified on hardware** (`769`/`770`
traffic carrying `0x00`/`0x80`/… exactly).

## Notes

**MIDI Maze is multiplayer: the MASTER waits for a SLAVE to join, so a single
node never starts a game** (see D-09). That's a game requirement, not a transport
bug. The byte pipe is validated for everything a single node can drive. Full
gameplay-rate validation needs a real 2nd node and lands in EPIC-03 (two STs via
the orchestrator, or the orchestrator faking a SLAVE). The RP stays protocol-dumb.
