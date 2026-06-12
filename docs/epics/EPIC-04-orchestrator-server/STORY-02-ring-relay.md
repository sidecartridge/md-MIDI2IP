---
id: STORY-02
epic: EPIC-04
title: Ring relay (single global ring)
status: done
milestone: alpha-mvp
---

## Goal

Wire the connected players into a MIDI Maze **ring** by forwarding bytes: each
player's OUT stream goes to the **next** player's IN. The server is byte-agnostic
and never interprets MIDI Maze (D-02).

## Tasks

- [x] `Registry.next_player` defines the ring (insertion order, wrapping); single global ring for the MVP
- [x] Forward each player's OUT bytes to the next player's IN verbatim (`write` + `drain`, `TCP_NODELAY` from STORY-01), single source per target
- [x] Ring re-forms on join/leave (`next_player` computed fresh each chunk); **a lone node has no peer and receives no self-echo** (it must not elect/count before the ring forms, D-04), 2 players = A↔B
- [x] Counters: source `bytes_out` on read, target `bytes_in` on forward; in-order, no drop within a connection

## Acceptance

With N players connected, bytes one player sends arrive at the next player in
order; joining/leaving re-forms the ring without corrupting other players' streams.

## Notes

This is the network analogue of the physical MIDI daisy-chain. The game protocol
(master election, COUNT-PLAYERS, lock-step) runs over the ring transparently; the
server needs no awareness of it. A **lone node gets nothing back** (no self-echo):
echoing it would let it win master election and count players before a second node
joins, so it would never see the latecomer (D-04). It waits until the ring forms.
