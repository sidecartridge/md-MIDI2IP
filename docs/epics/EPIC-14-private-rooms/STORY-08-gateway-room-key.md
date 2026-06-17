---
id: STORY-08
epic: EPIC-14
title: Hatari gateway room key (--room)
status: todo
---

## Goal

A Hatari node joins a room with `--room` over WebSocket.

## Tasks

- [ ] Add `--room <key>` to `gateway.py` (used with `--transport ws`)
- [ ] Send `Authorization: Bearer <key>` in the gateway WS handshake (`ws_handshake`) when a room is set
- [ ] Normalize the key to uppercase so it matches the orchestrator and the firmware
- [ ] Document that `--room` needs `--transport ws`; a tcp gateway uses the default room
- [ ] selftest: the gateway handshake request carries the `Authorization: Bearer` header with the normalized room

## Acceptance

A Hatari `ws` node with `--room DIEGOROOM` joins that room; with no `--room` it joins the
default room. selftest confirms the header is sent.

## Notes

Sequenced before the firmware room key (STORY-09) on purpose: the gateway is the
known-good, quick-to-iterate client, so it proves the room routing and provisioning
end to end before the firmware. Reuses the EPIC-13 gateway WS client (`ws_handshake` /
`_WsSocket`); this adds the room argument and the one header line.
