---
id: EPIC-14
iteration: 5
title: Private rooms (room-key MIDI rings)
status: done
---

## Goal

Turn the single global ring into multiple private rings keyed by a human-typed room key.
Players that enter the same room key share their own MIDI Maze ring, isolated from other
rooms (room key `DIEGOROOM` gives everyone who typed it one private ring). A WebSocket node
presents its room key in the handshake as `Authorization: Bearer <roomkey>`, and the
orchestrator routes it to that room's ring. Rooms are pre-provisioned by an operator
through a small REST API, so a join with an unknown key is refused. The web view gains a
room selector so an operator can watch any room. Rooms are a WebSocket feature; a plain-TCP
node joins a single default ring.

## Scope

- In scope: a per-room ring registry on the orchestrator (replacing the single ring); the
  `Authorization: Bearer` room key on the WebSocket handshake; a REST API to provision
  rooms (admin-key for writes, reads open); reject-unknown-room on join; room lifecycle (a
  16-player cap, auto-generated short codes, an empty-room TTL); persistence of provisioned
  rooms across a restart; a room-aware `status.json` plus a room selector, per-room game
  phase and master badge, and a lobby page in the web view; a firmware room-key config and
  boot-menu entry; a Hatari gateway `--room` flag; the decision (D-14) and a contract
  update.
- Out of scope: per-player auth beyond the room key (the key is the shared secret for a
  ring); `wss` / TLS (still deferred; terminate TLS and guard the REST API at a reverse
  proxy); room selection over plain TCP (TCP uses the default room); orchestrator-side
  drones / bots (MIDI-Maze-aware logic, a later smart epic per D-09); match recording and
  replay.

## Stories

- STORY-01: Room model, REST contract, and decision (D-14)
- STORY-02: Orchestrator per-room rings (default room + WS room routing)
- STORY-03: Orchestrator REST provisioning API (admin-key writes, reject unknown)
- STORY-04: Room lifecycle (16-player cap, auto-generated codes, empty-room TTL)
- STORY-05: Room persistence across an orchestrator restart
- STORY-06: Room-aware status.json + web ring-view room selector
- STORY-07: Per-room observability (game phase, master badge, lobby page)
- STORY-08: Hatari gateway room key (--room) (proves the room path before the firmware)
- STORY-09: Firmware room key (config + boot menu + Bearer handshake header)
- STORY-10: Validate private rooms on hardware (two isolated rings, ST + Hatari)

## Notes

The room key is the shared secret for a ring (D-14): easy to type (case-insensitive,
short, alphanumeric), carried as `Authorization: Bearer` on the WebSocket handshake, and
matched against the pre-provisioned rooms. Without TLS the key travels in clear text, so it
gates a ring rather than securing the traffic; put TLS and the REST admin guard behind a
reverse proxy for an exposed deployment. Builds on EPIC-13 (the WebSocket carrier). The
per-room byte stream and ring semantics are unchanged (D-02, D-04, C-01); routing simply
gains a room dimension. References: D-02 (opaque bytes), D-04 (ring routing), D-13
(WebSocket transport).
