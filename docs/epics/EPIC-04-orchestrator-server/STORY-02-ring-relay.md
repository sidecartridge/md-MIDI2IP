---
id: STORY-02
epic: EPIC-04
title: Ring relay (single global ring)
status: in-progress
milestone: alpha-mvp
---

## Goal

Wire the connected players into a MIDI Maze **ring** by forwarding bytes: each
player's OUT stream goes to the **next** player's IN. Byte-agnostic — the server
never interprets MIDI Maze (D-02).

## Tasks

- [x] `Registry.next_player` defines the ring (insertion order, wrapping); single global ring for the MVP
- [x] Forward each player's OUT bytes to the next player's IN verbatim (`write` + `drain`, `TCP_NODELAY` from STORY-01), single source per target
- [x] Ring re-forms on join/leave (`next_player` computed fresh each chunk); **1 player = self-loop/echo** (the faithful ring-of-one), 2 players = A↔B
- [x] Counters: source `bytes_out` on read, target `bytes_in` on forward; in-order, no drop within a connection

## Acceptance

With N players connected, bytes one player sends arrive at the next player in
order; joining/leaving re-forms the ring without corrupting other players' streams.

## Notes

This is the network analogue of the physical MIDI daisy-chain. The game protocol
(master election, COUNT-PLAYERS, lock-step) runs over the ring transparently — the
server needs no awareness of it. Define the 1-player case explicitly (self-loop vs
idle) since it affects single-node behaviour.
