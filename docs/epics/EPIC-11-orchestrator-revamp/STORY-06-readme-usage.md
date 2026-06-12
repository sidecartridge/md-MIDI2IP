---
id: STORY-06
epic: EPIC-11
title: Document end-user usage in README.md (Multi-device RP2040 + Hatari)
status: done
---

## Goal

Add a user-facing **Usage** section to README.md so a player can go from a flashed
cartridge (or Hatari) to a running MIDI Maze match over IP, without reading the code
or the epics.

## Tasks

- [x] **SidecarTridge Multi-device (RP2040):** flash the UF2 to the Pico, seat the board in the cartridge slot, boot the Atari ST, set the orchestrator host/port in the boot menu, launch the firmware ([E]), then run MIDI Maze and pick "MIDI" networking
- [x] **Hatari node:** run the EPIC-05 gateway (Hatari MIDI ↔ FIFO ↔ orchestrator) so a software player joins the same ring — the documented Hatari invocation + the gateway command
- [x] **Orchestrator:** run `orchestrator/orchestrator.py` (host/port), open the HTTP ring page to watch nodes, and note `--inspect` for protocol logging and `--no-http` for lock-step runs
- [x] A minimal **2-node walkthrough** (one RP-hardware node + one Hatari node through one orchestrator) that reaches master election and plays
- [x] Keep it accurate to the current build/flags and stdlib-only (no extra deps); link to CLAUDE.md/build.sh for build/flash mechanics rather than duplicating them

## Acceptance

README.md has a self-contained "Usage" section a new user can follow end to end: flash
or run a node, configure the orchestrator endpoint, start the orchestrator, and play a
2-node match — for both the RP2040 cartridge and a Hatari peer.

## Notes

Pulls together the user-facing surface of EPIC-03 (RP endpoint config), EPIC-05
(Hatari gateway), EPIC-06 (boot menu / endpoint screens), and EPIC-11 (the orchestrator
+ its ring page). Build/flash internals stay in CLAUDE.md / build.sh; this is the
player's view, not the developer's.
