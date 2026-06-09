---
id: STORY-02
epic: EPIC-03
title: Drain the OUT ring → network send
status: todo
milestone: alpha-mvp
---

## Goal

Replace the OUT side of EPIC-02's RP-local echo: instead of copying drained
OUT-ring bytes into the IN ring, send them to the orchestrator with low added
latency.

## Tasks

- [ ] Take drained OUT bytes from the chandler callback and queue for send
- [ ] Forward bytes verbatim — no MIDI parsing/filtering/framing (D-02)
- [ ] Flush promptly (small coalescing window) to stay within the latency budget (C-01)
- [ ] Handle partial sends / backpressure from lwIP without losing bytes

## Acceptance

Bytes the ST emits appear at the orchestrator in order; measured added latency is
within target (set in EPIC-05).

## Notes

MIDI Maze is latency-sensitive (C-01); avoid large buffering, coalesce only
within a few ms. The stream is opaque bytes (D-02) — never reorder or drop.
