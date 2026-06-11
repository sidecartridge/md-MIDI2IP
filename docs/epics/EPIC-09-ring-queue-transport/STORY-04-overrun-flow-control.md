---
id: STORY-04
epic: EPIC-09
title: IN-ring overrun & flow-control policy
status: todo
---

## Goal

Define and implement what happens when the RP (network producer) outruns the ST's
`Bconin` drain and the IN ring fills — the one remaining correctness gap of the
fire-and-forget design.

## Tasks

- [ ] Size the IN ring for the worst-case burst (the SEND-DATA maze) with margin
- [ ] Track ring occupancy on the RP from `write_idx - read_idx` (read_idx advanced by the bit-9 signals)
- [ ] Decide + implement the full-ring policy: backpressure the network (stop reading the socket) vs. drop, and surface it (status/log)
- [ ] Mirror the question for OUT: the RP's network OUT queue under a sustained burst
- [ ] Instrument occupancy / overruns for the hardware validation (STORY-05)

## Acceptance

Under a sustained worst-case burst the IN path never silently corrupts the stream —
it either keeps up or applies a defined, observable policy.

## Notes

The bit-9 advances are the RP's only view of consumption, so flow control hangs off
them. MIDI's ~3 KB/s vs a multi-KB ring makes overrun unlikely, but the maze burst is
the case to size for.
