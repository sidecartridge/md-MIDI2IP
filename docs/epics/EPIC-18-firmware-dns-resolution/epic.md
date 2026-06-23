---
id: EPIC-18
iteration: 8
title: Firmware orchestrator hostname (DNS) resolution
status: todo
---

## Goal

Let the RP2040 firmware reach the orchestrator by **hostname**, not just a numeric
IP. Now that the orchestrator is deployable behind a domain (EPIC-17 — e.g.
`midimaze.sidecartridge.com` on Cloudflare), the `MIDI_HOST` endpoint must accept a
DNS name and resolve it before connecting.

## Scope

- In scope: resolve `MIDI_HOST` via lwIP DNS in the connect path (`rp/src/midi.c`),
  keeping the numeric-IP fast path, with a clean fallback to the existing reconnect
  backoff on DNS failure/timeout.
- Out of scope: TLS / `wss` (D-13); the config UI (the `[H]ost` boot menu already
  accepts an arbitrary string); the orchestrator/Docker side (its DNS works).

## Background

`midi_net_try_connect()` used `ipaddr_aton(midiNetHost, &ip)` — which parses only a
dotted-quad — and returned silently otherwise, so a hostname never connected (the
`MIDI_HOST` config comment even said "IP for now"). lwIP `LWIP_DNS` and `LWIP_DHCP`
are already enabled (`lwipopts.h:52,56`) and DNS servers arrive via DHCP (or the
static `WIFI_DNS` config), so only the connect path needed wiring.

## Stories

- STORY-01: Resolve the orchestrator host via lwIP DNS

## Notes

- `dns_gethostbyname` is async in poll mode: `ERR_OK` (cached) connects inline,
  `ERR_INPROGRESS` connects from the `dns_found` callback, else reset -> backoff.
- Connect path: `rp/src/midi.c:448`.
