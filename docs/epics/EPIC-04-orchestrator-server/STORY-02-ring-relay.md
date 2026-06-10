---
id: STORY-02
epic: EPIC-04
title: Ring relay (single global ring)
status: todo
milestone: alpha-mvp
---

## Goal

Wire the connected players into a MIDI Maze **ring** by forwarding bytes: each
player's OUT stream goes to the **next** player's IN. Byte-agnostic — the server
never interprets MIDI Maze (D-02).

## Tasks

- [ ] Maintain a ring order over the connection registry; for the MVP, all connected players form **one** ring
- [ ] Forward each player's received (OUT) bytes to the next player in the ring (their IN), verbatim, promptly (no Nagle, no batching beyond a tiny coalesce)
- [ ] Re-form the ring cleanly on join/leave (a 2-player ring is A↔B; 1 player relays to itself or idles — define it)
- [ ] Update OUT/IN byte counters; never reorder or drop within a connection

## Acceptance

With N players connected, bytes one player sends arrive at the next player in
order; joining/leaving re-forms the ring without corrupting other players' streams.

## Notes

This is the network analogue of the physical MIDI daisy-chain. The game protocol
(master election, COUNT-PLAYERS, lock-step) runs over the ring transparently — the
server needs no awareness of it. Define the 1-player case explicitly (self-loop vs
idle) since it affects single-node behaviour.
