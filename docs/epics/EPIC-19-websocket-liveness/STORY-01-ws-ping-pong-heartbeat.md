---
id: STORY-01
epic: EPIC-19
title: WS ping/pong heartbeat + eviction
status: done
---

## Goal

A silently-dropped WebSocket node is evicted from the ring within the idle timeout,
while a live-but-idle player (which pongs) stays connected.

## Tasks

- [x] `WsConn` tracks `last_rx` (time of any inbound frame, incl. pong) and gains a
      `ping()` (unmasked server->client WS ping).
- [x] Per-WS-connection `_ws_heartbeat` task: ping every `WS_PING_INTERVAL_S`; evict
      via `_drop_player` if no inbound frame for `WS_IDLE_TIMEOUT_S`.
- [x] Spawn it for WS carriers in `handle_conn`; cancel it in `finally`. TCP carriers
      keep relying on TCP keepalive.
- [x] Verified locally: a non-ponging WS client is dropped within the idle timeout
      (evicted ~1.2 s with a 1.0 s test timeout); the orchestrator selftest still
      passes.

## Acceptance

A WS peer that drops ungracefully (or stops responding) is evicted within
~`WS_IDLE_TIMEOUT_S` and removed from the ring; live idle players (which pong) are
unaffected. Detection is ~30 s with the shipped constants.

## Notes

This traverses the nginx proxy (EPIC-17) where TCP keepalive could not — the proxy
forwards the WS ping/pong end to end.
