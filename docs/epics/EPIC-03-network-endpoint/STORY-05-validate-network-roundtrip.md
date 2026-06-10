---
id: STORY-05
epic: EPIC-03
title: Validate the network round-trip (echo peer)
status: done
milestone: alpha-mvp
---

## Goal

Prove the RP networking end to end with a trivial desktop **echo peer** (a few
lines of Python: accept TCP, echo every byte back). With it, MIDI Maze's handshake
round-trips over the wire — the network analogue of EPIC-02's RP echo. This is the
RP-side validation that fits a single ST.

## Tasks

- [x] Stand up an echo peer (`tools/echo_peer.py`) and point the firmware at it
- [x] MIDI Maze becomes MASTER with bytes proven to cross the network and return
- [x] Byte-exact, in-order round-trip (no loss/reorder) over the link
- [x] A peer drop is recovered automatically — killing/restarting the echo peer reconnects (STORY-04 backoff), LED blink→steady, `ping` down→up

## Acceptance

Against the echo peer, MIDI Maze reaches MASTER + config exactly as it did over
the EPIC-02 local echo — now with the bytes travelling ST → RP → network → RP → ST.

## Notes

This validates the *transport over the network* — the same bar D-09 sets for a
single node. **It will not start a match** (echo = ring-of-one): that needs a real
2nd node, which is the orchestrator's job (relay two STs, or fake a SLAVE) in its
own repo. Full 2-player gameplay is validated there + a final integration, not in
this RP epic.
