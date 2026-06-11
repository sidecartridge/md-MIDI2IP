---
id: STORY-02
epic: EPIC-07
title: Validate — physical ST + Hatari node: election/slave/names work, game launch doesn't
status: done
milestone: alpha-mvp
---

## Goal

Capture how far a real MIDI Maze match gets on hardware: a **physical Atari ST**
running MIDI Maze (through its RP) and a **second node running in Hatari**, both
connected to the orchestrator (a mixed hardware/software ring). Record exactly
which protocol phases succeed and where it stops — the empirical boundary of the
current transport.

## Tasks

- [x] A physical Atari ST running MIDI Maze (via its RP) and a second node in Hatari both connect to the orchestrator — a mixed hardware/software ring forms
- [x] **Master election works**: one node becomes MASTER, the other SLAVE (the `0x00` election byte round-trips through the ring)
- [x] **COUNT-PLAYERS + NAME-DIALOG work**: the player count settles and the **user names exchange** around the ring (`0x86`)
- [x] **Game launch does NOT work yet**: START-GAME / the ~4 KB `SEND-DATA` maze can't complete over the RP-hardware path — the D-12 throughput ceiling, which is the boundary this story documents

## Acceptance

On real hardware (physical ST + a Hatari node through the orchestrator) the ring
forms, the nodes elect master/slave, and user names exchange — but **launching the
game does not yet succeed**. The boundary matches the D-12 prediction (the per-byte
throughput ceiling bites exactly at the large SEND-DATA transfer).

## Notes

The protocol-level companion to STORY-01's raw throughput measurement: everything
up to and including NAME-DIALOG is low-volume and works fine; the game launch is
the first high-volume transfer (~4 KB maze) and is where the ~970 bytes/s ceiling
(D-12) stops the match. The fix lives in EPIC-09 (ring-queue transport); the full
hardware match is re-validated in EPIC-10 STORY-02 once that lands.
