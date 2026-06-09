---
id: STORY-02
epic: EPIC-02
title: m68k producer/consumer with flow control
status: todo
milestone: alpha-mvp
---

## Goal

Implement the m68k-side ring access used by the EPIC-01 hooks: push to OUT, pop
from IN, and report fullness/emptiness for back-pressure.

## Tasks

- [ ] OUT push helper (advance tail, handle wrap, detect full)
- [ ] IN pop helper (advance head, handle wrap, detect empty)
- [ ] Signal the RP when OUT has data (command sentinel / send_sync)
- [ ] Back-pressure path for `Bcostat`/`Midiws` when OUT is full

## Acceptance

Stress test from the ST (a sustained byte stream + a burst) shows no byte loss
or corruption and no lockup when the ring saturates.

## Notes

Keep helpers tiny — they run inside trap handlers within the 6 KB `userfw.s`
budget.
