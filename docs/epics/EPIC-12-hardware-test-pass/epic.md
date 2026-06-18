---
id: EPIC-12
iteration: 3
title: Hardware test pass (Atari ST + Hatari)
status: done
---

## Goal

A repeatable manual test pass that verifies a release build of MIDI-to-IP on real gear
before shipping. The setup under test is a physical Atari ST with the SidecarTridge
Multi-device plus a Hatari node through the gateway, both driven against one
orchestrator. Earlier hardware epics proved the architecture (EPIC-07) and confirmed a
playable 2-player match once the transport was fixed (EPIC-10). This epic turns that
into a written checklist so any build can be re-verified the same way, and it adds the
multi-node and recovery paths that were never run end to end.

## Scope

- In scope: a manual test checklist covering boot and config, ring join and
  observability, the full MIDI Maze protocol and gameplay on a mixed ST + Hatari ring,
  multi-node behaviour up to 16 players, plus the disconnect and reconnect recovery
  paths. Run on a real ST (Booster-installed firmware) and a Hatari node.
- Out of scope: automated hardware-in-the-loop testing (descoped in EPIC-10 STORY-01,
  no ST is attached to CI); the build CI gate (already green, EPIC-10 STORY-01); any
  code change. This epic runs and records tests, opening a follow-up story if a test
  fails.

## Stories

- STORY-01: Boot, config and node bring-up (ST via Booster + Hatari via gateway)
- STORY-02: Ring join and orchestrator observability
- STORY-03: Full MIDI Maze match on a mixed ST + Hatari ring
- STORY-04: Multi-node scaling and recovery paths

## Notes

Continuation of EPIC-07 and EPIC-10. Those validated that a match works; this epic is
the standing verification checklist for each release. Record the result of each run in
the story Acceptance sections or a dated note, and open a bug story for any failure.
References: C-01 (lock-step latency), D-02 (dumb byte pipe), EPIC-05 (the Hatari
gateway), EPIC-11 (the orchestrator observability the tests read).
