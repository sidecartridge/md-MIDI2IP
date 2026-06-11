---
id: STORY-04
epic: EPIC-08
title: Validate — Hatari MIDI Maze + smart orchestrator (single node)
status: done
milestone: alpha-mvp
---

## Goal

Prove the smart orchestrator is correct against a **real MIDI Maze client**: a
single MIDI Maze instance running in Hatari (via the EPIC-05 gateway), connected to
the orchestrator with the coordination layer (`--coordinate`) active, brings up
cleanly and the inferred protocol state matches. This validates EPIC-08's logic
independently of the RP-hardware throughput ceiling (D-12).

## Tasks

- [x] A single Hatari MIDI Maze node connects through the gateway to the orchestrator running with `--coordinate` (the smart layer active)
- [x] The node reaches MASTER via the ring-of-one self-echo, with `RingState` / master-protection running and **not** interfering with the single-node bring-up
- [x] `--inspect` decodes the node's MASTER-ELECT / COUNT-PLAYERS traffic; `status.json` reflects the inferred master + phase
- [x] Confirms the coordination layer is sound against a real client (the full 2-player hardware match stays in EPIC-10, gated on D-12)

## Acceptance

A single Hatari MIDI Maze instance + the orchestrator with `--coordinate` brings up
cleanly — the node becomes MASTER, and the orchestrator's inferred state (master /
phase) matches what `--inspect` shows.

## Notes

This is the smart orchestrator's real-client check that *can* be done without the
transport fix: a lone node only exercises election + the coordinator's state, not
the high-throughput gameplay/SEND-DATA path (that needs ≥2 players and is blocked
by D-12). A full 2-player match on hardware is EPIC-10 STORY-02. Replaces the
earlier "validate a full 2-player match" story, which moved to EPIC-10.
