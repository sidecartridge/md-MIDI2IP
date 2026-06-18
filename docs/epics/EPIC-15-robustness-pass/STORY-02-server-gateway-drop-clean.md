---
id: STORY-02
epic: EPIC-15
title: Confirm the orchestrator and gateway drop everything on disconnect
status: todo
---

## Goal

When a connection drops, neither the orchestrator nor the gateway keeps queued, buffered,
or partial-frame bytes that could leak into another node or a later session.

## Tasks

- [ ] Orchestrator: confirm dropping a player removes it from its room, closes the writer (discarding its transport write buffer), and drops its WS decoder state; verify no bytes destined for the dropped player linger in another player's buffer beyond what was already delivered
- [ ] Gateway: confirm a disconnect ends the bridge with no partial WS frame or buffered bytes carried over; the `_WsSocket` decoder and its initial buffer do not survive into a new socket
- [ ] Add selftest coverage: after a player drops and a new player joins the same room, the new player receives only post-join bytes, with no replay of the dropped player's queued traffic
- [ ] Document the buffering model (where bytes can sit, and that a close discards them) in the orchestrator README or the contract

## Acceptance

The selftest shows a drop then rejoin replays nothing, and neither the orchestrator nor the
gateway holds a per-connection byte queue beyond the transport buffer that a close discards.

## Notes

The orchestrator relays directly (no per-player app queue) and bounds the write buffer at
`WRITE_BUFFER_HIGH`; a close discards it. Pairs with the firmware-side flush (STORY-02) so
no side replays stale bytes after a reconnect.
