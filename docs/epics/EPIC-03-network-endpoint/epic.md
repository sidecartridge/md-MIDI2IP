---
id: EPIC-03
title: RP network endpoint
status: todo
---

## Goal

Carry the MIDI byte streams between the RP firmware and a configured remote
endpoint over the network (Wi-Fi / lwIP), in both directions, with reconnection
and clear link status.

## Scope

- In scope: connection lifecycle to a configured host:port, sending drained OUT
  bytes, receiving bytes into the IN ring, and error/reconnect handling.
- Out of scope: where the config comes from (EPIC-04) and the ring mechanics
  (EPIC-02). Wire framing/protocol choice is decided in STORY-01 here.

## Stories

- STORY-01 — Connection lifecycle to configured host:port
- STORY-02 — MIDI OUT bytes → network send
- STORY-03 — Network receive → MIDI IN bytes
- STORY-04 — Error handling, reconnect, link status
- STORY-05 — Extend the self-test harness over the network round-trip
- STORY-06 — Endpoint liveness ping command

## Notes

Use the existing `network.c` / lwIP poll-mode plumbing. Transport is decided: raw
byte stream over TCP + `TCP_NODELAY` (D-02/D-03) to a central Python orchestrator
(D-04/D-08), a separate project.
