---
id: STORY-04
epic: EPIC-04
title: Robustness — half-open detection, buffers, shutdown
status: todo
---

## Goal

Keep the server stable across the messy realities of player connections: ungraceful
drops, slow/half-open links, and clean shutdown.

## Tasks

- [ ] Detect a silently-dead player (TCP keepalive, like `tools/echo_peer.py`) and remove it from the ring promptly
- [ ] Bound per-connection buffers; a slow/stuck player must not let memory grow unbounded or stall the whole ring
- [ ] Clean shutdown (Ctrl-C / signal): close sockets, drain, exit without tracebacks
- [ ] Defensive logging on errors; one bad connection never takes down the server

## Acceptance

Killing a player ungracefully removes it and re-forms the ring within seconds; a
slow player doesn't exhaust memory or freeze others; Ctrl-C exits cleanly.

## Notes

Mirrors the hardening already in `tools/echo_peer.py` (keepalive, supersede stale,
catch errors), scaled to N concurrent players. Decide the policy when a slow
player can't keep up (drop bytes vs disconnect it) and log it — don't silently
stall the ring.
