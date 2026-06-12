---
id: STORY-02
epic: EPIC-11
title: Stale relay-buffer cleanup — drop pending IN/OUT after 10 s
status: todo
---

## Goal

Mirror the firmware's stale-queue policy (EPIC-09 STORY-04) on the orchestrator: if a
node's relay buffers (bytes queued to or from it) sit undrained past a timeout, drop
them so a stalled or slow node can't replay stale traffic into a resumed ring.

## Tasks

- [ ] Track a last-progress timestamp per node for the inbound and outbound relay buffers
- [ ] Drop buffered bytes (and log it) when a buffer has made no progress for `STALE_SECONDS` (10 s, a module constant)
- [ ] Compose cleanly with the existing slow-player drop / bounded write buffers — flush stale data without double-dropping or killing a healthy-but-busy node
- [ ] Expose a per-node stale-flush count for the telemetry feed (STORY-04)

## Acceptance

A node that stalls ≥10 s has its pending IN/OUT bytes flushed (and logged), and a
resumed node rejoins with a clean buffer instead of replaying old data. Healthy nodes
under load are unaffected.

## Notes

10 s is conservative vs. the firmware's 1 s (`MIDI_QUEUE_STALE_MS`) — the orchestrator
sees whole sessions, not the lock-step ring, so it should only catch genuine stalls.
Tunable constant.
