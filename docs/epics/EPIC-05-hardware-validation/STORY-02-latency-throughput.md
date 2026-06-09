---
id: STORY-02
epic: EPIC-05
title: Latency/throughput measurement & tuning
status: todo
---

## Goal

Quantify added per-hop latency and sustained throughput, set targets **relative
to the original physical MIDI ring speed**, and tune buffering/coalescing to meet
them.

## Tasks

- [ ] Define the target as per-hop latency ≤ physical MIDI ring-speed-per-hop (~hundreds of µs at 31250 baud + per-machine processing) — we intercept before the ACIA, so this should be achievable or better on a LAN (C-01)
- [ ] Measure per-hop round-trip latency (write → orchestrator → readback) for single events
- [ ] Measure sustained throughput for the per-frame state burst and confirm the resulting FPS vs original
- [ ] Tune ring sizes and send coalescing to hit targets; record results

## Acceptance

Measured per-hop latency matches or beats the original ring-speed-per-hop, the
resulting frame rate is at least on par with the physical game, and results are
written up here.

## Notes

MIDI Maze is lock-step (C-01): latency sets FPS and a late readback can freeze
the game, so the target is per-hop, not an absolute. Feeds back into EPIC-02
(ring sizes) and EPIC-03 STORY-02 (coalescing window).
