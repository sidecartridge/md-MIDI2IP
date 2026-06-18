---
id: STORY-10
epic: EPIC-14
title: Validate private rooms on hardware (two isolated rings, ST + Hatari)
status: done
---

## Goal

Two private rooms on real gear: players in different rooms cannot see each other, and a
room of ST + Hatari plays a full match.

## Tasks

- [x] Provision two rooms over REST with the admin key; confirm `GET /rooms` lists both
- [x] Two nodes that entered room key A play together; a node with room key B is isolated (absent from A's ring and traffic)
- [x] Play a full MIDI Maze match inside a room (ST on `ws` with a room key + Hatari on `ws --room`), election through gameplay
- [x] The ring view room selector shows each room's ring independently
- [x] A join with an unprovisioned key is refused

## Acceptance

Private rooms isolate play on real hardware, provisioning and rejection behave per D-14,
and the UI selects rooms. Add a row to the EPIC-12 checklist referencing this run.

## Notes

Hardware verification, so it follows the EPIC-12 conventions. Depends on STORY-02 through
STORY-09. The TCP default-room path stays available for nodes that do not use a room.
