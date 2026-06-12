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

- [x] **Overview:** what MIDI Maze and the MIDI ring are, with ASCII diagrams of the physical ring and the network-relayed ring
- [x] **Applications inventory:** enumerate the repo's apps (microfirmware, orchestrator, Hatari gateway) and how to get each running
- [x] **SidecarTridge Multi-device (RP2040):** install from the **Booster** app (download + launch, like any microfirmware, not manual UF2 flashing), set the orchestrator host/port via `[H]ost`/`[P]ort`, launch with `[E]xit to GEM`, then run MIDI Maze
- [x] **Hatari node:** run the EPIC-05 gateway (Hatari MIDI ↔ FIFO ↔ orchestrator) so a software player joins the same ring, with the documented Hatari invocation + the gateway command
- [x] **Orchestrator:** run `orchestrator/orchestrator.py` (host/port), open the HTTP ring page to watch nodes, and note `--inspect` for protocol logging and `--no-http` for lock-step runs
- [x] **Play a match:** up to 16 participants in one ring, any mix of real ST+SidecarTridge and Hatari+gateway nodes on one orchestrator
- [x] Keep it accurate (Booster install, current flags), user-facing in tone (cf. the drives_emulator microfirmware docs), and stdlib-only for the Python apps

## Acceptance

README.md has a self-contained "Usage" section a new user can follow end to end: flash
or run a node, configure the orchestrator endpoint, start the orchestrator, and play a
2-node match, covering both the RP2040 cartridge and a Hatari peer.

## Notes

Pulls together the user-facing surface of EPIC-03 (RP endpoint config), EPIC-05
(Hatari gateway), EPIC-06 (boot menu / endpoint screens), and EPIC-11 (the orchestrator
+ its ring page). Build/flash internals stay in CLAUDE.md / build.sh; this is the
player's view, not the developer's.
