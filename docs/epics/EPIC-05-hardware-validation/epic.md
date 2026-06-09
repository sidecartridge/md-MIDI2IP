---
id: EPIC-05
title: Hardware validation
status: todo
---

## Goal

Prove the end-to-end path on real hardware against a desktop peer, and measure
latency/throughput so MIDI timing is acceptable for real use.

## Scope

- In scope: a desktop loopback/bridge peer, functional end-to-end tests,
  latency/throughput measurement and tuning, and the automated hardware-in-the-
  loop regression gate that ties the self-test harness together.
- Out of scope: host-side unit tests (there is no such suite; verification is
  build + on-hardware self-test per `CLAUDE.md`).

## Stories

- STORY-01 — Loopback against a desktop network-MIDI bridge
- STORY-02 — Latency/throughput measurement & tuning
- STORY-03 — Automated end-to-end regression run (CI gate)

## Notes

"Verification" here means: build succeeds, UF2 boots on hardware, and observed
behaviour over the serial debug console + a connected synth/DAW.
