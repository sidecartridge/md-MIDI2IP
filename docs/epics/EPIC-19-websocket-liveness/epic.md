---
id: EPIC-19
iteration: 9
title: WebSocket liveness — evict silently-dropped nodes
status: in-progress
---

## Goal

Detect and evict a WebSocket player whose peer vanished without a clean close, so a
phantom node no longer lingers in the ring and breaks gameplay. This is critical
behind the nginx proxy (EPIC-17), where the orchestrator's TCP peer is the
always-alive proxy and TCP keepalive cannot see a dead browser.

## Scope

- In scope: an orchestrator-driven WebSocket ping/pong heartbeat that evicts a WS
  player with no inbound frame (data or pong) within an idle timeout.
- Out of scope: TCP carriers (the existing ~10 s TCP keepalive already reaps them);
  client changes (browsers/firmware/gateway already answer pings with a pong).

## Background

Behind a reverse proxy the orchestrator<->nginx socket stays alive, so the existing
~10 s TCP keepalive (`_enable_keepalive`) never fires for a dead browser and the
phantom persisted for minutes, breaking the ring. WebSocket control frames traverse
the proxy transparently, so a server-driven ping/pong is the reliable cross-proxy
liveness signal.

## Stories

- STORY-01: WS ping/pong heartbeat + eviction

## Notes

- Ping every `WS_PING_INTERVAL_S` (10 s); evict if the last inbound frame is older
  than `WS_IDLE_TIMEOUT_S` (30 s). `orchestrator.py`: `WsConn.last_rx`/`ping()`,
  `_ws_heartbeat`, spawned per WS connection in `handle_conn`.
