---
id: STORY-03
epic: EPIC-12
title: Full MIDI Maze match on a mixed ST + Hatari ring
status: todo
---

## Goal

Two players, one on the physical ST and one in Hatari, play a full MIDI Maze match over
IP through the orchestrator.

## Tasks

- [ ] From GEM, run MIDI Maze on the ST node and join the match on the Hatari node
- [ ] Master election settles: one node MASTER, one SLAVE (the `0x00` election byte round-trips the ring)
- [ ] COUNT-PLAYERS settles the player count and NAME-DIALOG exchanges user names (`0x86`; `Player #…` ASCII visible under `--inspect`)
- [ ] START-GAME and the ~4 KB SEND-DATA maze transfer complete without loss (the transfer that hit the old D-12 ceiling)
- [ ] Both players enter the maze and JOYSTICK-DATA flows both ways at a playable frame rate (C-01)
- [ ] The match plays through its lifecycle (start, play, end) and restarts without re-booting the nodes

## Acceptance

A mixed ST + Hatari ring elects master, exchanges names, launches the game, and plays a
responsive match end to end (C-01). Note the observed frame rate and any stall.

## Notes

This is the EPIC-10 STORY-02 match made repeatable across node types. The SEND-DATA
transfer is the high-volume step that the EPIC-09 fast path unblocked.
