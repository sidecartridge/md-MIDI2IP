---
id: STORY-04
epic: EPIC-02
title: Extend the self-test harness across the real ring transport
status: todo
milestone: alpha-mvp
---

## Goal

Evolve the EPIC-01 STORY-05 self-test so it exercises the *real* ring transport
(STORY-02 producer/consumer + STORY-03 chandler drain/fill) instead of the crude
RP `OUT→IN` echo scaffold. The network still doesn't exist yet, so the loop
closes on the RP — but now through the actual transport code.

## Tasks

- [ ] Point the self-test at the real ring helpers, retiring the EPIC-01 echo scaffold
- [ ] RP echo at the transport boundary (drained OUT bytes → IN fill) to close the loop pre-network
- [ ] Cover ring wrap and full/empty conditions; assert ordering and zero byte loss
- [ ] Extend the serial verdict with ring high-water and overflow counters

## Acceptance

A test build reports `MIDI-SELFTEST: PASS n/n` with bytes flowing through the
real rings (not the scaffold); a deliberately undersized ring surfaces as a
`FAIL` with overflow counts rather than silent loss.

## Notes

Builds on EPIC-01 STORY-05 (same cartridge self-test + serial verdict channel).
Once EPIC-03 lands, the RP boundary echo here is replaced by the network peer in
EPIC-03 STORY-05.
