---
id: STORY-01
epic: EPIC-04
title: asyncio TCP server + connection registry
status: todo
milestone: alpha-mvp
---

## Goal

Stand up the `orchestrator/` server: an `asyncio` TCP listener that accepts player
connections and tracks them in an in-memory registry. Stdlib only.

## Tasks

- [ ] `asyncio` TCP server bound to a configurable host:port (default `0.0.0.0:5005`)
- [ ] On connect, register the player: id, peer address, connect time, OUT/IN byte counters
- [ ] On disconnect, deregister; expose the registry to the ring relay (STORY-02) and HTTP (STORY-03)
- [ ] `TCP_NODELAY` on each accepted socket (latency, C-01); structured logging of connect/disconnect

## Acceptance

Multiple clients can connect concurrently; each appears in the registry with live
byte counters; disconnects are reflected promptly. No third-party imports.

## Notes

`tools/echo_peer.py` is the reference for socket setup (REUSEADDR, NODELAY,
keepalive). asyncio is stdlib — satisfies the no-external-libraries rule and
matches D-08. Bytes are opaque (D-02) — this story doesn't move them between
players yet (that's STORY-02).
