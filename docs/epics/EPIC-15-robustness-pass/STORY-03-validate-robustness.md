---
id: STORY-03
epic: EPIC-15
title: Validate the robustness fixes on hardware
status: todo
---

## Goal

A reconnect no longer leaves stale bytes that poison the ring on real gear.

## Tasks

- [ ] Drop a node during the setup / config screen, reconnect, and confirm no stale bytes desync the ring
- [ ] Drop a node mid-game, reconnect, and confirm the firmware does not replay pre-drop OUT bytes
- [ ] Play a full match after a reconnect and confirm no replayed bytes corrupt the game
- [ ] Record the results against the EPIC-12 checklist

## Acceptance

A reconnect mid-session does not poison the ring, and no side replays pre-drop bytes on
hardware.

## Notes

Hardware verification, so it follows the EPIC-12 conventions. Depends on STORY-01 (the
firmware flush) and STORY-02 (the orchestrator and gateway confirmation).
