---
id: EPIC-07
title: Hardware validation
status: todo
---

## Goal

Validate the full stack on real hardware and keep it healthy: latency/throughput
measurement so MIDI timing stays acceptable, and an automated regression gate that
runs the whole ST → RP → network → orchestrator path. The per-epic loopback
validations (EPIC-01/02/03) prove each layer; EPIC-07 is the cross-cutting,
measured, automatable validation.

## Scope

- In scope: latency/throughput measurement and tuning, and an automated
  hardware-in-the-loop regression gate (a cartridge-resident self-test exerciser +
  serial verdict over the full stack).
- Out of scope: the test peer itself — that's the **Hatari gateway (EPIC-05)**,
  which replaced the old "desktop test peer" idea; and host-side unit tests (there
  is no such suite; verification is build + on-hardware behaviour per `CLAUDE.md`).

## Stories

- STORY-01 — Latency/throughput measurement & tuning
- STORY-02 — Automated regression gate (self-test over the full stack)

## Notes

"Verification" here means: build succeeds, UF2 boots on hardware, and observed
behaviour over the serial debug console — exercised against a real peer (a 2nd
ST+RP, or the EPIC-05 Hatari gateway).
