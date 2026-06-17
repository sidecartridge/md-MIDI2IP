---
id: STORY-02
epic: EPIC-14
title: Orchestrator per-room rings (default room + WS room routing)
status: todo
---

## Goal

The orchestrator holds one ring per room. A WebSocket node is routed to its room from the
`Authorization: Bearer` header; TCP nodes and keyless WS nodes join the default room; the
relay stays within a room.

## Tasks

- [ ] Introduce a room registry mapping a normalized room key to its own `Registry` (one ring each), replacing the single global registry; `next_player` and the relay operate within a node's room
- [ ] Parse `Authorization: Bearer <key>` in `handle_ws`, normalize the key (uppercase), and assign the connection to that room
- [ ] Route TCP connections and WS connections with no room key to the default room (preserves today's single-ring behavior)
- [ ] Keep per-connection dedup, reconnection recycling, and telemetry scoped to the room
- [ ] Auto-create a room on first join for now (a stub); STORY-03 switches this to pre-provisioned with reject-unknown
- [ ] selftest: two WS nodes in room A relay to each other byte-exact; a node in room B receives none of room A's traffic (isolation)

## Acceptance

Nodes are grouped into per-room rings and relay only within their room; the default room
carries TCP and keyless nodes; the selftest proves room isolation. Builds on EPIC-13
STORY-03 (the WS listener and the transport-agnostic relay).

## Notes

This story builds the multi-ring structure and routing. The reject-unknown enforcement and
the REST provisioning land in STORY-03; until then rooms auto-create so isolation is
testable.
