---
id: STORY-01
epic: EPIC-04
title: asyncio TCP server + connection registry
status: done
milestone: alpha-mvp
---

## Goal

Stand up the `orchestrator/` server: an `asyncio` TCP listener that accepts player
connections and tracks them in an in-memory registry. Stdlib only.

## Tasks

- [x] `asyncio` TCP server (`asyncio.start_server`) bound to a configurable host:port (`--host`/`--port`, default `0.0.0.0:5005`)
- [x] On connect, register the `Player` (id, peer, connect time, `bytes_out`/`bytes_in`); reads + counts incoming bytes (discarded until STORY-02)
- [x] On disconnect, deregister; the shared `registry` is exposed for the ring relay (STORY-02) and HTTP (STORY-03)
- [x] `TCP_NODELAY` on each accepted socket; structured `logging` of connect/disconnect with counters + online count

## Acceptance

Multiple clients can connect concurrently; each appears in the registry with live
byte counters; disconnects are reflected promptly. No third-party imports.

## Notes

`tools/echo_peer.py` is the reference for socket setup (REUSEADDR, NODELAY,
keepalive). asyncio is stdlib — satisfies the no-external-libraries rule and
matches D-08. Bytes are opaque (D-02) — this story doesn't move them between
players yet (that's STORY-02).
