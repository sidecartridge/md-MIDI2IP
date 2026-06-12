---
id: STORY-04
epic: EPIC-11
title: Per-node telemetry in status.json: IP, host, bytes in/out
status: done
---

## Goal

Turn `status.json` into a per-node telemetry feed the UI can poll: for each connected
node, its IP, reverse-DNS host (STORY-03), and bytes-in / bytes-out counters, plus the
ring ordering so the page can draw the ring.

## Tasks

- [x] Define the `status.json` shape: `players` is a node list **in ring order**, each `{id, ip, host, peer, connected_s, idle_s, bytes_out, bytes_in}`, plus a top-level `ring` (id sequence) and `uptime_s`/`listen`/`players_online`
- [x] Maintain per-node bytes-in / bytes-out counters on the relay path (cheap increments, already tracked)
- [x] Include per-node `connected_s` (up-time) and `idle_s` (seconds since last byte, which lets the UI dim a stalled node; replaces STORY-02's dropped stale-flush count)
- [x] Keep the JSON a race-free snapshot taken from the asyncio loop (as today)
- [x] Document the schema (docstring on `_status_snapshot`) so the HTML (STORY-05) and external tooling can rely on it

## Acceptance

`GET /status.json` returns a per-node array (IP, host, bytes in/out, ring position,
up-time, idle) that updates live and is safe to poll every 2 s. **Met**: selftest
asserts the per-node shape and that `players` is in `ring` order.

## Notes

Replaces the `RingState`-derived `protocol` block removed in STORY-01. `bytes_out` is
received FROM the node (its MIDI OUT), `bytes_in` is sent TO it: the exact data the
ring overlay (STORY-05) renders. `idle_s` derives from the STORY-02 `last_active`.
