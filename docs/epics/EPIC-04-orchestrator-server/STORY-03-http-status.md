---
id: STORY-03
epic: EPIC-04
title: HTTP status interface
status: done
milestone: alpha-mvp
---

## Goal

Expose server status over HTTP so you can see what's happening in a browser or
scrape it. Stdlib `http.server` (or an asyncio HTTP handler), on a **separate
port** from the game TCP server.

## Tasks

- [x] HTTP responder on its own port (`--http-port`, default `8080`), a 2nd `asyncio.start_server` in the same loop
- [x] **HTML** page (auto-refresh): uptime, listen addr, player count, the ring order, and a per-player table (id, peer, connect time, OUT/IN bytes)
- [x] **JSON** endpoint `/status.json` with the same snapshot (`json.dumps`), machine-readable
- [x] Read-only and race-free: same loop as the relay (no `http.server` thread, no locks), never blocks it

## Acceptance

Hitting the HTTP port in a browser shows live server + player + ring info; the
JSON endpoint returns the same data parseably. Opening it never stalls byte relay.

## Notes

MVP shows **connections and the current ring**, not parsed game sessions.
"Gameplays disputing / disputed" history needs MIDI-Maze awareness, which is a
later **smart** epic (the JSON shape can leave room for it). If `http.server`'s
threading is awkward with asyncio, a minimal asyncio HTTP responder is fine;
still stdlib only.
