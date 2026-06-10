---
id: STORY-04
epic: EPIC-08
title: Validate — a full 2-player MIDI Maze match starts and plays
status: todo
milestone: alpha-mvp
---

## Goal

The payoff: two players actually **play a MIDI Maze match over IP**, end to end —
ST+RP and Hatari+gateway (the 2nd node, D-09) through the orchestrator.

## Tasks

- [ ] Full handshake confirmed in `--inspect`: election → **COUNT-PLAYERS(=2)** → NAME-DIALOG → START-GAME → **SEND-DATA intact**
- [ ] The match **starts** (both enter the maze) and JOYSTICK-DATA flows both ways at a playable frame rate (C-01)
- [ ] **TERMINATE-GAME** ends the match cleanly for both nodes
- [ ] Capture a full clean-match `--inspect` trace as the regression reference (hands off to EPIC-07)

## Acceptance

Two players start and play a MIDI Maze match over the orchestrator; the
`--inspect` trace shows the complete protocol sequence with no desync, and the
game is responsive enough to play (C-01).

## Notes

This closes the loop on EPIC-01..05 + EPIC-08. Depends on STORY-02 (election) and
STORY-03 (SEND-DATA flow-control). The measured/automated version of this is
EPIC-07 (latency measurement + regression gate); this story is the first
hand-played match.
