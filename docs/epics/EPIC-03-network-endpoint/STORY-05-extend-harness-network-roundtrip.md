---
id: STORY-05
epic: EPIC-03
title: Extend the self-test harness over the network round-trip
status: todo
milestone: alpha-mvp
---

## Goal

Evolve the self-test (EPIC-01 STORY-05, extended in EPIC-02 STORY-04) so the
bytes traverse the *real* network: ST → rings → RP → network → host peer → back
→ ST. This validates the full data path end-to-end.

## Tasks

- [ ] Host echo peer that reflects the MIDI stream back to the firmware (matches EPIC-03 STORY-01 transport)
- [ ] Run the self-test through the full stack and assert byte-exact round-trip
- [ ] Exercise reconnect mid-test and assert recovery (per EPIC-03 STORY-04)
- [ ] Serial verdict includes round-trip byte counts and link-state transitions

## Acceptance

A test build with the host echo peer running reports `MIDI-SELFTEST: PASS n/n`
with bytes proven to cross the network and return; pulling the peer mid-test
yields a recorded reconnect and still converges to PASS (or a clear FAIL).

## Notes

Replaces the EPIC-02 RP boundary echo with a real network peer. The host echo
peer is the same desktop bridge used in EPIC-05 STORY-01 — share the tooling.
