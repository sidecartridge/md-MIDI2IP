---
id: STORY-05
epic: EPIC-14
title: Room persistence across an orchestrator restart
status: done
---

## Goal

Provisioned rooms survive an orchestrator restart, so an operator does not re-create them
every time.

## Tasks

- [x] Persist the provisioned room list (key plus metadata: created-at, optional name) to a JSON file at `--rooms-file` (default alongside the orchestrator)
- [x] Load the file on startup so the rooms exist again after a restart; the default room is implicit and not stored
- [x] Write on every create / delete; tolerate a missing or corrupt file by starting empty and logging a warning
- [x] Keep it stdlib (`json` + a plain file), no database
- [x] selftest: create a room, reload from the file (or restart the server in the harness), and the room is still present and joinable; a missing file starts clean

## Acceptance

Rooms created over REST are restored after a restart, and a missing or corrupt file is
handled without crashing. selftest proves a created room survives a reload.

## Notes

Builds on STORY-03 (REST provisioning). Per-room player state is not persisted (players
reconnect into the room); only the room set is saved. This closes the "rooms live in
memory" gap noted in the epic scope.
