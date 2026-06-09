---
id: EPIC-03
title: RP network endpoint
status: todo
---

## Goal

Move the loopback one more layer out: replace EPIC-02's **RP-local OUT→IN echo**
with a **network round-trip to the orchestrator**. The RP sends OUT-ring bytes to
the Python orchestrator (separate repo) and fills the IN ring from it; the
orchestrator wires the MIDI Maze ring among players. Deliverable: **2-player
MIDI Maze over IP**. The m68k hooks and shared-region rings are unchanged from
EPIC-01/02 — only the RP's echo becomes a network exchange.

## Scope

- In scope: connection lifecycle to the orchestrator, draining the OUT ring to
  the network, filling the IN ring from the network, reconnect/link status, and
  validating real multiplayer.
- Out of scope: where the config comes from (EPIC-04) and the ring mechanics
  (EPIC-02). The wire format is already decided (raw bytes / TCP, D-02/D-03).

## Stories

- STORY-01 — Connection lifecycle to the orchestrator
- STORY-02 — Drain the OUT ring → network send
- STORY-03 — Network receive → fill the IN ring
- STORY-04 — Error handling, reconnect, link status
- STORY-05 — Validate: 2-player MIDI Maze over IP
- STORY-06 — Endpoint liveness ping command

## Notes

Use the existing `network.c` / lwIP poll-mode plumbing. Transport is decided: raw
byte stream over TCP + `TCP_NODELAY` (D-02/D-03) to a central Python orchestrator
(D-04/D-08), a separate project.
