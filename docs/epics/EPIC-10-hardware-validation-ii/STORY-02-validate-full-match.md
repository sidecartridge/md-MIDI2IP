---
id: STORY-02
epic: EPIC-10
title: Validate — a full 2-player MIDI Maze match starts and plays
status: done
milestone: alpha-mvp
---

## Goal

The payoff: two players actually **play a MIDI Maze match over IP**, end to end —
ST+RP and a second node through the orchestrator.

## Tasks

- [x] Full handshake confirmed: election → COUNT-PLAYERS → NAME-DIALOG (names seen, `Player #…` ASCII in the byte stream) → START-GAME → SEND-DATA intact
- [x] The match **starts** (both enter the maze) and JOYSTICK-DATA flows both ways at a playable frame rate (C-01)
- [x] Match lifecycle works on the RP-hardware path (start → play → end)
- [x] Validated on real hardware as the reference for the EPIC-09 transport

## Acceptance

Two players start and play a MIDI Maze match over the orchestrator, responsive enough
to play (C-01). **Met** — confirmed on real hardware: "it works and it is playable."

## Notes

Closes the loop on EPIC-01..05 + EPIC-08 over the new EPIC-09 fast-path transport.
Validation was hands-on gameplay on the RP-hardware path (the deferred EPIC-08
STORY-04), which is what unblocked once EPIC-09 landed.
