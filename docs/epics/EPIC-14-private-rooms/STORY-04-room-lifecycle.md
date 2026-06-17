---
id: STORY-04
epic: EPIC-14
title: Room lifecycle (16-player cap, auto-generated codes, empty-room TTL)
status: todo
---

## Goal

Keep rooms sane: cap a ring at the MIDI Maze player limit, let the REST API mint short
throwaway room codes, and reap rooms that have gone empty.

## Tasks

- [ ] Cap a room at 16 players (the MIDI Maze ring limit); reject an over-cap join at the WS handshake (HTTP 403 "room full"). The default room is capped too
- [ ] Auto-generate a short room code: `POST /rooms` with no key returns a random code (uppercase, ambiguous characters like `O`/`0`/`I`/`1` removed) so an operator can mint a quick room; a named key (`DIEGOROOM`) still works
- [ ] Empty-room TTL: reap a non-default room that has had zero players for `ROOM_TTL` (default 10 min, overridable for tests); never reap the default room
- [ ] Report a room's player count against its cap in `status.json` / `/rooms` and in the logs
- [ ] selftest: the 17th join is refused; `POST` with no key returns a usable code that then accepts a join; an emptied room is reaped after a short test TTL; the default room is never reaped

## Acceptance

A room never exceeds 16 players, `POST /rooms` can mint a code or take a named key, empty
rooms self-clean after the TTL, and the default room persists. selftest covers each.

## Notes

Builds on STORY-02 (per-room rings) and STORY-03 (REST). The cap matches D-04 (a ring is
bounded; COUNT-PLAYERS breaks past 16). The reaper keeps the registry tidy for throwaway
auto-code rooms.
