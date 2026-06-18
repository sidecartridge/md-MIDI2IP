---
id: STORY-07
epic: EPIC-14
title: Per-room observability (game phase, master badge, lobby page)
status: done
---

## Goal

Show what each room is doing: its game phase, which node is master, and a lobby that lists
every room at a glance.

## Tasks

- [x] Run a per-room `MidiMazeInspector` off the relay path (read-only, D-02) to derive a room phase (idle / electing / counting / in-game) and the current master node
- [x] Add `phase` and `master` to the room's `status.json` and a per-room summary (count, cap, phase) to `/rooms`
- [x] Ring view: badge the room's phase and highlight the master node
- [x] Lobby page: a top-level page listing every room with its player count, cap, and phase, linking into each room's ring view
- [x] selftest: feed a known byte sequence and the room's phase + master are reported; `/rooms` carries per-room phase and counts; the lobby page lists rooms and links to the ring view

## Acceptance

Each room shows its phase and master in the ring view, the lobby lists all rooms with
counts and phase, and detection stays read-only (no effect on the relay). selftest covers
the phase decode, the `/rooms` summary, and the lobby page.

## Notes

Reuses the existing `MidiMazeInspector` (the `--inspect` decoder) per room, off the relay
path, so it is free of D-02 risk. Builds on STORY-06 (room-scoped status + selector) and
the EPIC-13 ring view.
