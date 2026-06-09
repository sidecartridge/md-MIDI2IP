---
id: STORY-05
epic: EPIC-03
title: Validate — 2-player MIDI Maze over IP
status: todo
milestone: alpha-mvp
---

## Goal

Confirm the loopback has reached its final form — a **network round-trip** — by
playing real multiplayer: two Atari STs (each with the cartridge) connected
through the orchestrator play MIDI Maze against each other over IP. This is
EPIC-03's per-epic validation, the network analogue of EPIC-01's local loopback
and EPIC-02's RP-mediated one.

## Tasks

- [ ] Two STs join via the orchestrator; the ring forms (master election, COUNT-PLAYERS) over IP
- [ ] In-game: each player sees the other move; gameplay stays in sync
- [ ] Byte-exact, in-order delivery across the network (no desync)
- [ ] Exercise a mid-game reconnect (per STORY-04) and confirm recovery or a clean end

## Acceptance

Two STs play a MIDI Maze session against each other over IP via the orchestrator,
in sync, with no desync or freeze under normal network conditions.

## Notes

Single-developer testing (one ST) can use the orchestrator's loopback/test peer
from EPIC-05 STORY-01 to stand in for the second player. Latency/throughput
measurement and the automated regression gate live in EPIC-05.
