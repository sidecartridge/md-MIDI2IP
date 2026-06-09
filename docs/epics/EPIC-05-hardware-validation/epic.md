---
id: EPIC-05
title: Hardware validation
status: todo
---

## Goal

Validate the full stack on real hardware and keep it healthy: a desktop test peer
for single-ST testing, latency/throughput measurement so MIDI timing stays
acceptable, and an automated regression gate that runs the whole
ST → RP → network path. The per-epic loopback validations (EPIC-01/02/03) prove
each layer; EPIC-05 is the cross-cutting, measured, automatable validation.

## Scope

- In scope: a desktop test peer / network-MIDI bridge, latency/throughput
  measurement and tuning, and an automated hardware-in-the-loop regression gate
  (a cartridge-resident self-test exerciser + serial verdict over the full stack).
- Out of scope: host-side unit tests (there is no such suite; verification is
  build + on-hardware behaviour per `CLAUDE.md`).

## Stories

- STORY-01 — Desktop test peer / network-MIDI bridge
- STORY-02 — Latency/throughput measurement & tuning
- STORY-03 — Automated regression gate (self-test over the full stack)

## Notes

"Verification" here means: build succeeds, UF2 boots on hardware, and observed
behaviour over the serial debug console + a connected synth/DAW.
