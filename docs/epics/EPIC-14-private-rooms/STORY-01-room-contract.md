---
id: STORY-01
epic: EPIC-14
title: Room model, REST contract, and decision (D-14)
status: todo
---

## Goal

Settle the room model before code: the key format, the `Authorization: Bearer` handshake
header, WS-only rooms with a default room for TCP, pre-provisioned rooms with
reject-unknown, the REST endpoints and admin auth, and the room-aware status / UI. Record
it as D-14 and extend the orchestrator contract.

## Tasks

- [ ] Add D-14 to `DECISIONS.md`: a room key defines a private ring; players sharing a key share a ring; the key rides the WebSocket handshake as `Authorization: Bearer <roomkey>`; a plain-TCP node joins a default room; rooms are pre-provisioned via REST and an unknown key is refused; the key gates a ring, it is not transport security (no TLS, D-13)
- [ ] Specify the room key format: case-insensitive (normalized to uppercase), `A-Z 0-9`, 1 to 16 characters (fits `SETTINGS_MAX_VALUE_LENGTH` and is easy to type on the firmware menu); an empty key means the default room
- [ ] Specify the REST API on the HTTP status port: `GET /rooms` (list, open), `POST /rooms` with a key (create, admin), `DELETE /rooms/{key}` (delete, admin); admin auth via an `X-Admin-Key` header matched against `--admin-key` (writes refused when `--admin-key` is unset)
- [ ] Specify routing: one ring per room; relay only within a room; a default room (always present) carries TCP nodes and WS nodes with no key
- [ ] Specify status / UI: `GET /status.json?room=KEY` returns one room's snapshot; `GET /rooms` feeds a room selector in the ring view
- [ ] Specify room lifecycle: a 16-player cap per room (D-04, the MIDI Maze ring limit); `POST /rooms` may mint a short auto code or take a named key; an empty non-default room is reaped after a TTL
- [ ] Specify persistence: provisioned rooms are saved to a JSON file and reloaded on restart (the default room is implicit)
- [ ] Specify observability: a per-room phase (from the read-only inspector) and master node, surfaced in `status.json`, `/rooms`, the ring view, and a lobby page
- [ ] Extend `ORCHESTRATOR-CONTRACT.md` with a "Rooms" section (key format, Bearer header, provisioning, per-room routing, lifecycle, status, observability) referencing D-14

## Acceptance

D-14 is in `DECISIONS.md`, and `ORCHESTRATOR-CONTRACT.md` has a Rooms section that the
other stories implement against. No code in this story.

## Notes

The shared spec for the epic. Builds on the EPIC-13 Transport section; rooms are layered on
the WebSocket carrier without changing the per-room byte stream (D-02).
