---
id: STORY-04
epic: EPIC-09
title: IN/OUT overrun, flow-control & stale-queue policy
status: done
---

## Goal

Define and implement what happens when a side outruns the other and a queue fills —
the remaining correctness gap of the fire-and-forget design. Covers both the IN ring
(RP network producer vs. ST `Bconin`) and the OUT ring (ST `Bconout` burst vs. TCP).

## Tasks

- [x] Size the IN ring for the worst-case burst (the SEND-DATA maze) with margin — 16 KB
- [x] Track ring occupancy on the RP from `head - tail` (tail advanced by the bit-9 signals)
- [x] Full-ring policy: drop on full (`midi_in_push` returns false), plus a **time-based stale flush** — if a queue's consumer makes no progress for `MIDI_QUEUE_STALE_MS` (1000 ms), the pending bytes are stale (a stall would replay old traffic and desync the ring), so flush them; logs `MIDI IN/OUT stale: flushed N`
- [x] Mirror for OUT: a 16 KB OUT ring filled from the hot path, drained to TCP in the poll context up to `tcp_sndbuf` (retries instead of dropping) — fixes the burst `tcp_write` drop (`OUT > RX`)
- [x] Instrument occupancy / overruns (`outdrop`, the `MIDI/s` rate line — now `#if 0`, re-enable to measure)

## Acceptance

Under a sustained worst-case burst the IN path never silently corrupts the stream —
it either keeps up or applies a defined, observable policy. **Met** — the maze burst
round-trips without loss (`OUT == RX == IN_adv`), and the stale flush only fires on a
genuine ≥1 s stall.

## Notes

The bit-9 advances are the RP's only view of consumption, so flow control hangs off
them. The OUT-side drop turned out to be the more pressing overrun in practice (the
burst overran `tcp_write`, not the IN ring). The stale flush is each queue's
"last drain" timestamp (a real drain, or an empty→fill that restarts the window) vs.
`MIDI_QUEUE_STALE_MS`. Open: a true network-backpressure path (stop reading the
socket) is not implemented — drop + stale-flush is the current policy.
