---
id: STORY-02
epic: EPIC-11
title: Reconnection node recycling — supersede a stalled prior same-IP connection
status: done
---

## Goal

When a node reconnects from an IP that already has a connection, recycle its node
number: if the prior connection is stalled (a dead/half-open node that never FIN'd),
drop it and give the reconnection a fresh, incremented node id — so a reset node
rejoins cleanly instead of leaving a phantom.

## Tasks

- [x] Track per-node liveness (`last_active` = event-loop time of the last byte received), stamped on connect and every relayed chunk
- [x] `_is_stalled(player, now)` = no OUT bytes for `RECONNECT_STALE_S` (10 s, a module constant)
- [x] On a new connection from an IP that already has a node: drop the prior same-IP connection when it's a private LAN address (one-per-IP) **or** stalled (any IP class, incl. loopback / NAT); the reconnection always gets a fresh incremented id
- [x] Confirm `selftest.py` passes (fresh node not stalled; quiet node stalled past threshold)

## Acceptance

A node that reconnects from the same IP supersedes its stalled prior connection and is
assigned a new incremented node number; a still-active connection from an exempt IP
(loopback/NAT) is left alone. Selftest green. **Met.**

## Notes

Replaces the original "stale relay-buffer cleanup" scope: the relay forwards each
chunk immediately (no per-node byte queue to age out), so the meaningful staleness is
at the **connection** level. This extends the existing one-per-private-IP dedup
(EPIC-04 STORY-04) — which always supersedes a private-IP node — to also drop a
*stalled* prior connection for IP classes that are exempt from the strict dedup, so a
reconnecting loopback/NAT node doesn't leave a phantom. `RECONNECT_STALE_S` is tunable.
