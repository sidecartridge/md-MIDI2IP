---
id: STORY-04
epic: EPIC-11
title: Per-node telemetry in status.json — IP, host, bytes in/out
status: todo
---

## Goal

Turn `status.json` into a per-node telemetry feed the UI can poll: for each connected
node, its IP, reverse-DNS host (STORY-03), and bytes-in / bytes-out counters, plus the
ring ordering so the page can draw the ring.

## Tasks

- [ ] Define the `status.json` shape: a node list in ring order, each `{id, ip, host, bytes_in, bytes_out, uptime, stale_flushes, ...}`
- [ ] Maintain per-node bytes-in / bytes-out counters on the relay path (cheap increments)
- [ ] Include the stale-flush count (STORY-02) and per-node connect/up-time
- [ ] Keep the JSON a race-free snapshot taken from the asyncio loop (as today)
- [ ] Document the schema so the HTML (STORY-05) and any external tooling can rely on it

## Acceptance

`GET /status.json` returns a per-node array (IP, host, bytes in/out, ring position,
up-time) that updates live and is safe to poll every 2 s.

## Notes

Replaces the `RingState`-derived status fields removed in STORY-01. These counters are
exactly the data the ring overlay (STORY-05) renders — design the shape with the
visualization in mind.
