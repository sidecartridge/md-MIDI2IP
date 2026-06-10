---
id: STORY-01
epic: EPIC-03
title: Connection lifecycle to configured host:port
status: done
milestone: alpha-mvp
---

## Goal

Establish and maintain a connection to the configured remote MIDI endpoint, and
expose its state to the rest of the firmware.

## Tasks

- [x] Raw-byte TCP client (lwIP `tcp_*`, NO_SYS poll mode) + `tcp_nagle_disable` = `TCP_NODELAY` (D-02/D-03) — no protocol layer
- [x] Connect once Wi-Fi has an IP; driven by `midi_net_poll()` in the main loop, retrying every `MIDI_NET_RETRY_MS`
- [x] Track state (`MIDI_NET_DOWN` / `CONNECTING` / `UP`) with connect/recv/err callbacks
- [x] Clean teardown implemented (`midi_net_reset` on peer-close/error/reset); config-driven enable/disable is out of scope here, tracked in EPIC-04 (per-app endpoint config)

## Dev endpoint

Hardcoded in `rp/src/midi.c`: `MIDI_NET_HOST` / `MIDI_NET_PORT` (`5005`). Set
`MIDI_NET_HOST` to the LAN IP of the machine running `tools/echo_peer.py`, then
rebuild + reflash. EPIC-04 replaces this with per-app config.

## Acceptance

Firmware reaches "up" against a known-good peer, and a deliberate peer shutdown
moves it to "down" without crashing or stalling the bus loop.

**Verified on hardware:** `MIDI net: connected to <peer>:5005` against
`tools/echo_peer.py`; the link stays up and idle (no MIDI crosses it yet —
that's STORY-02/03).

## Notes

Wi-Fi STA association is a precondition handled by the platform (global `gconfig`
`WIFI_*` keys + `network.c`); this story owns only the endpoint socket on top of
an already-up link. Poll-mode lwIP — no blocking sockets. Endpoint config is
provided by EPIC-04. The endpoint is the Python orchestrator (D-04/D-08), a
separate project; this firmware is a TCP client to it.
