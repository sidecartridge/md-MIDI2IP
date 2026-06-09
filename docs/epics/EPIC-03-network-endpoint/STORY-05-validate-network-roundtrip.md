---
id: STORY-05
epic: EPIC-03
title: Validate the network round-trip (echo peer)
status: todo
milestone: alpha-mvp
---

## Goal

Prove the RP networking end to end with a trivial desktop **echo peer** (a few
lines of Python: accept TCP, echo every byte back). With it, MIDI Maze's handshake
round-trips over the wire — the network analogue of EPIC-02's RP echo. This is the
RP-side validation that fits a single ST.

## Tasks

- [ ] Stand up an echo peer (TCP accept; echo bytes back) and point the firmware at it
- [ ] MIDI Maze becomes MASTER and reaches the config screen, with bytes proven to cross the network and return
- [ ] Byte-exact, in-order round-trip (no loss/reorder) over the link
- [ ] A peer drop mid-handshake is recovered (per STORY-04)

## Acceptance

Against the echo peer, MIDI Maze reaches MASTER + config exactly as it did over
the EPIC-02 local echo — now with the bytes travelling ST → RP → network → RP → ST.

## Notes

This validates the *transport over the network* — the same bar D-09 sets for a
single node. **It will not start a match** (echo = ring-of-one): that needs a real
2nd node, which is the orchestrator's job (relay two STs, or fake a SLAVE) in its
own repo. Full 2-player gameplay is validated there + a final integration, not in
this RP epic.
