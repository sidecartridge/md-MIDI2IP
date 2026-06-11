---
id: STORY-01
epic: EPIC-10
title: Automated regression gate (self-test over the full stack)
status: todo
milestone: alpha-mvp
---

## Goal

A single repeatable command that validates the whole real stack and gives a clear
pass/fail — the project's regression gate. The per-epic loopback validations
(EPIC-01/02/03) prove each layer interactively; this automates a full-stack run
so regressions are caught without a human reading the ST screen.

## Tasks

- [ ] Cartridge-resident self-test exerciser (gated to a test build): drive a deterministic MIDI pattern through the hooks and check the bytes that come back
- [ ] Verdict channel: write pass/fail + counters to a shared-region slot; the RP prints `MIDI-SELFTEST: PASS|FAIL n/m` over serial
- [ ] Run it over the full path (ST → RP → network → orchestrator → back) using the EPIC-05 Hatari gateway (and/or a 2nd ST) as the peer
- [ ] One command: build the test build, reset the ST, capture serial, assert PASS; document how to triage a FAIL (which layer's counters)

## Acceptance

The single command, against attached hardware + the test peer, returns a clean
pass/fail; a regression at any layer is caught and the serial counters point at
the failing stage. The self-test code is excluded from release builds.

## Notes

This is where the cartridge self-test lives (it was descoped from the EPIC-01 MVP,
which is validated interactively via the loopback). Hardware-in-the-loop, so it
may stay a documented local/bench run if CI has no ST attached — state that
limitation rather than implying full CI coverage.
