---
id: STORY-03
epic: EPIC-05
title: Automated end-to-end regression run (CI gate)
status: todo
milestone: alpha-mvp
---

## Goal

Turn the layered self-test harness (EPIC-01 STORY-05 → EPIC-02 STORY-04 →
EPIC-03 STORY-05) into a single repeatable command that validates the full real
stack and gives a clear pass/fail — the regression gate for the project.

## Tasks

- [ ] One command: build the test build, reset the ST, capture the serial console
- [ ] Assert `MIDI-SELFTEST: PASS` across the full ST → rings → RP → network → peer → back path
- [ ] Wire into repo CI (or document the manual hardware-in-the-loop run if CI lacks hardware)
- [ ] Document pass criteria and how to triage a FAIL (which layer's counters to read)

## Acceptance

Running the single command against attached hardware + host peer returns a clean
pass/fail; a regression introduced at any layer is caught and points at the
failing stage via its serial counters.

## Notes

This is the culmination of the harness thread, not a new harness. Hardware-in-
the-loop, so it may stay a documented local/bench run if CI has no ST attached —
note that limitation explicitly rather than implying full CI coverage.
