---
id: STORY-02
epic: EPIC-08
title: Master-election coordinator (one stable master, any launch order)
status: todo
milestone: alpha-mvp
---

## Goal

Guarantee **exactly one stable MASTER** regardless of launch order, so
COUNT-PLAYERS completes. Today (hardware, D-11): machines launched
asynchronously each auto-elect; a SLAVE forwards every `0x00`, so with no single
master the election byte loops forever, and stray `0x00`s re-trigger election
*mid-count* — the MASTER reads 0 (or a garbage) player count and never starts.

## Tasks

- [ ] **Spike the rule**: lock in the first node whose `0x00` completes the ring as MASTER; decide **passive** (suppress conflicting `0x00`s once a master exists) vs **active** (orchestrator drives one clean election when the ring is stable for T ms)
- [ ] Once a master is locked, stop stray `0x00` MASTER-ELECT bytes from *other* nodes from resetting it until membership changes — so COUNT-PLAYERS isn't interrupted
- [ ] Re-run a clean election on membership change (join / drop) so the ring re-forms with a single master (D-04)
- [ ] Gate behind a flag: **off → pure dumb relay** (D-02/D-10, today's default); **on → coordinated**. Document exactly which bytes the orchestrator suppresses/injects

## Acceptance

Two machines launched in **any order** converge to exactly one MASTER, and
COUNT-PLAYERS returns the correct count (2) with no re-election storm — verified
in the `--inspect` trace.

## Notes

This is the **first** place the orchestrator stops being byte-dumb (D-02), so it
is opt-in and orchestrator-only (the RP/gateway stay dumb). Acts on STORY-01's
model. The exact suppress/inject rule is the spike's job — keep it the minimal
intervention that makes election converge, not a full protocol re-implementation.
