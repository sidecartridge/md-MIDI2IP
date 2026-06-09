---
id: STORY-01
epic: EPIC-03
title: Connection lifecycle to configured host:port
status: todo
milestone: alpha-mvp
---

## Goal

Establish and maintain a connection to the configured remote MIDI endpoint, and
expose its state to the rest of the firmware.

## Tasks

- [ ] Use raw-byte framing (D-02) over TCP + `TCP_NODELAY` (D-03) to the orchestrator — no protocol layer
- [ ] Open connection to configured host:port on startup / when enabled
- [ ] Track connection state (down / connecting / up)
- [ ] Tear down cleanly on disable or config change

## Acceptance

Firmware reaches "up" against a known-good peer, and a deliberate peer shutdown
moves it to "down" without crashing or stalling the bus loop.

## Notes

Wi-Fi STA association is a precondition handled by the platform (global `gconfig`
`WIFI_*` keys + `network.c`); this story owns only the endpoint socket on top of
an already-up link. Poll-mode lwIP — no blocking sockets. Endpoint config is
provided by EPIC-04. The endpoint is the Python orchestrator (D-04/D-08), a
separate project; this firmware is a TCP client to it.
