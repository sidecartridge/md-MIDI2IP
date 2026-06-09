---
id: STORY-02
epic: EPIC-03
title: MIDI OUT bytes → network send
status: todo
milestone: alpha-mvp
---

## Goal

Send the bytes drained from the OUT ring to the remote endpoint with low added
latency.

## Tasks

- [ ] Take drained OUT bytes from the chandler callback and queue for send
- [ ] Forward bytes verbatim — no MIDI parsing/filtering/framing (D-02)
- [ ] Flush promptly (small coalescing window) to stay within the latency budget (C-01)
- [ ] Handle partial sends / backpressure from lwIP without losing bytes

## Acceptance

Bytes the ST emits appear at the remote peer in order; measured added latency is
within target (set in EPIC-05).

## Notes

MIDI Maze is latency-sensitive (C-01); avoid large buffering, coalesce only
within a few ms. The stream is opaque bytes (D-02) — never reorder or drop.
