---
id: EPIC-07
iteration: 1
title: Hardware validation
status: done
---

## Goal

Measure and validate the full stack on real hardware: per-hop latency and sustained
throughput relative to the original physical MIDI ring speed (so MIDI timing can be
judged and tuned), and how far a real MIDI Maze match actually gets on a mixed
hardware/software ring. The per-epic loopback validations (EPIC-01/02/03) prove
each layer; EPIC-07 is the cross-cutting, measured validation.

## Scope

- In scope: latency/throughput measurement and tuning over the real stack.
- Out of scope: the automated regression gate (moved to Iteration 2
  as EPIC-10 Hardware validation II, since gating is premature while the transport
  is being redesigned per D-12); the test peer itself (that is the **Hatari gateway
  (EPIC-05)**); and host-side unit tests (verification is build + on-hardware
  behaviour per `CLAUDE.md`).

## Stories

- STORY-01: Latency/throughput measurement & tuning
- STORY-02: Validate: physical ST + Hatari node (election/slave/names work, game launch doesn't) (D-12)

## Notes

"Verification" here means: build succeeds, UF2 boots on hardware, and observed
behaviour over the serial debug console, exercised against a real peer (a 2nd
ST+RP, or the EPIC-05 Hatari gateway).

## Outcome (Iteration 1): complete

STORY-01 delivered the measurement. Its result is the single most important
finding of the iteration: the per-byte command handshake caps throughput at
**~970 bytes/s, ~3× slower than the original MIDI ring, and it can't be tuned
away** (D-12). The code result was "not playable," but the **research outcome is
valid and decisive**: it defines what Iteration 2 must fix (shared-memory rings
/ batching). The automated regression gate moved to **EPIC-10 (Hardware
validation II)** in Iteration 2, where it can run against the fixed transport.
