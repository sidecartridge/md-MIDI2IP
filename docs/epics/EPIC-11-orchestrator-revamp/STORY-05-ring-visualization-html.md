---
id: STORY-05
epic: EPIC-11
title: Revamped ring-visualization HTML page (polls status.json every 2 s)
status: done
---

## Goal

Replace the current static HTML status page with a fully revamped, self-contained page
that **draws the MIDI ring** and overlays each node's host/IP and bytes in/out,
refreshing from `status.json` every 2 seconds.

## Tasks

- [x] Serve a self-contained page (HTML/CSS/JS, no external/CDN deps) at `/`
- [x] Draw the ring: nodes placed around a circle with the relay direction indicated
- [x] Poll `/status.json` every 2 s and render each node's IP/host + bytes in/out as an overlay at its ring position
- [x] Handle 0 / 1 / N nodes gracefully (empty ring, single node, re-layout on join/leave)
- [x] Show connection/stale state visually (e.g. dim a stalled node) and degrade gracefully if `status.json` is unreachable

## Acceptance

Opening the orchestrator's HTTP page shows a live ring: nodes appear/disappear as they
join/leave, each labelled with its host/IP and byte counters, updating every 2 s with
no page reload.

## Notes

Self-contained and offline-friendly (served by the existing asyncio HTTP, no
framework). The 2 s poll matches the per-node telemetry cadence (STORY-04). Pairs
directly with STORY-04 — that story owns the data, this one owns the rendering.
