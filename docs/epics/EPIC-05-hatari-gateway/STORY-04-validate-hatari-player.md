---
id: STORY-04
epic: EPIC-05
title: Validate: Hatari MIDI Maze joins the ring as a player
status: done
milestone: alpha-mvp
---

## Goal

Prove the gateway end to end: MIDI Maze running in Hatari, bridged through the
gateway to the orchestrator, behaves as a real player in the ring. With a
second player, a match actually starts and plays.

## Tasks

- [x] Hatari runs MIDI Maze with the two FIFOs; the gateway connects to the orchestrator and the ring forms
- [x] Master election + COUNT-PLAYERS round-trip over the gateway (parity with the RP firmware's handshake)
- [x] With a **second** player (a real ST+RP, or a 2nd Hatari+gateway), a MIDI Maze match **starts and plays** in sync (closes the D-09 gap)
- [x] The orchestrator HTTP status shows the Hatari gateway as a connected player in the ring

## Acceptance

A Hatari MIDI Maze instance plays a real match through the orchestrator against a
second player, in sync, with the gateway appearing in the server status.

## Notes

This is the first time a **full match** is playable end to end (D-09 needed a 2nd
node; the gateway provides one purely in software). Two Hatari+gateway instances
on one laptop is the zero-hardware path; a real ST+RP vs a Hatari player is the
mixed path. Latency/throughput tuning lives in EPIC-07 STORY-01.
