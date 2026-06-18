---
id: STORY-06
epic: EPIC-14
title: Room-aware status.json + web ring-view room selector
status: done
---

## Goal

The web view shows one room at a time, chosen from a selector, and `status.json` is
per-room.

## Tasks

- [x] `GET /status.json?room=KEY` returns that room's snapshot (players, ring) in the existing schema; no param means the default room
- [x] `GET /rooms` returns the room list with a player count per room (also feeds the selector)
- [x] The ring view adds a room dropdown populated from `/rooms`; selecting a room polls `status.json?room=KEY` and draws that ring
- [x] Show the selected room key in the page header
- [x] selftest: `status.json?room=KEY` scopes to one room; `/rooms` lists rooms with counts; the page contains the selector and still draws the ring

## Acceptance

An operator can pick any room in the ring view and see only that room's ring; `status.json`
is room-scoped; `/rooms` lists rooms with their player counts.

## Notes

Extends the EPIC-11 telemetry and the EPIC-13 ring view. The per-node fields (id, ip, host,
transport, bytes) are unchanged; only the scope becomes a single room.
