---
id: STORY-03
epic: EPIC-04
title: HTTP status interface
status: todo
milestone: alpha-mvp
---

## Goal

Expose server status over HTTP so you can see what's happening in a browser or
scrape it. Stdlib `http.server` (or an asyncio HTTP handler), on a **separate
port** from the game TCP server.

## Tasks

- [ ] HTTP endpoint on its own port (default `8080`), served alongside the asyncio loop
- [ ] **HTML** page: server status (uptime, listen addr, player count), the connected players (id, peer addr, connect time, OUT/IN bytes), and the current ring order
- [ ] **JSON** endpoint (e.g. `/status.json`) with the same data, machine-readable
- [ ] Never blocks the relay loop; read-only (no control actions in the MVP)

## Acceptance

Hitting the HTTP port in a browser shows live server + player + ring info; the
JSON endpoint returns the same data parseably. Opening it never stalls byte relay.

## Notes

MVP shows **connections and the current ring**, not parsed game sessions —
"gameplays disputing / disputed" history needs MIDI-Maze awareness, which is a
later **smart** epic (the JSON shape can leave room for it). If `http.server`'s
threading is awkward with asyncio, a minimal asyncio HTTP responder is fine —
still stdlib only.
