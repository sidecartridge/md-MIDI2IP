---
id: STORY-06
epic: EPIC-03
title: Endpoint liveness ping command
status: done
---

## Goal

Give the user a way to confirm the orchestrator endpoint is alive, on demand,
without sending MIDI traffic.

## Design decision

We keep a **persistent, auto-reconnecting** connection to the orchestrator
(STORY-01/04), so an active TCP-connect probe would open a *second* connection to
the endpoint — semantically wrong for the real orchestrator (a connection = a
player). So `ping` is a **link-state report**: it reads the live state of the
existing connection (no probe traffic, no 2nd connection). RTT is replaced by
session uptime.

## Tasks

- [x] `ping` terminal command reports the orchestrator endpoint + link state (up / connecting / down) + session uptime when up
- [x] Instant and non-blocking — reads existing state, no network I/O, never stalls the bus loop
- [x] Output to the serial debug console (`PING <host>:<port> …`, machine-readable) and the terminal UI
- [x] Reachability is immediate: a dropped peer shows `down`/`connecting` as soon as the persistent link notices (STORY-04), so no separate probe timeout is needed

## Acceptance

`ping` against a live endpoint prints `up (<n>s)`; against a dead/again-down
endpoint it prints `down`/`connecting` — on both the serial console and the
terminal — without stalling the bus loop.

## Notes

Implemented via `midi_net_ping()` (reuses STORY-04 state) + a `cmdPing` entry in
the `emul.c` command table. The richer `status` command lives in EPIC-06 STORY-02.
