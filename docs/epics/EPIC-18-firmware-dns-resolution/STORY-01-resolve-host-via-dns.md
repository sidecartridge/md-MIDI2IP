---
id: STORY-01
epic: EPIC-18
title: Resolve the orchestrator host via lwIP DNS
status: done
---

## Goal

The firmware connects to the orchestrator given a **hostname** in `MIDI_HOST`, not
only a numeric IP.

## Tasks

- [x] Add `#include "lwip/dns.h"` to `rp/src/midi.c`.
- [x] Extract `midi_net_connect_to(ip)` (tcp_new + connect) shared by both paths.
- [x] In `midi_net_try_connect()`: keep `ipaddr_aton` for numeric IPs; otherwise call
      `dns_gethostbyname()` — connect inline on `ERR_OK`, from the callback on
      `ERR_INPROGRESS`, reset on any other error.
- [x] Add `midi_net_dns_found()`: connect on success; on `NULL` (fail/timeout) reset
      so the existing reconnect backoff retries.
- [x] Mark the attempt in progress (state = `MIDI_NET_CONNECTING`) so the poll loop
      does not launch a second resolve.

## Acceptance

`MIDI_HOST` set to a DNS name (the deployed domain) resolves and connects; a numeric
IP still connects directly; an unresolvable name falls back to the reconnect backoff
(no hang). Verified on hardware against the deployed orchestrator.

## Notes

lwIP DNS servers come from DHCP or the static `WIFI_DNS` config; `LWIP_DNS` is
already enabled. Debug build for serial verification:
`DEBUG_MODE=1 ./build.sh pico_w debug <APP_UUID>`.
