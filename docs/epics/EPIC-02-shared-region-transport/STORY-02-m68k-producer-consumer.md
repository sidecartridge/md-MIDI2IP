---
id: STORY-02
epic: EPIC-02
title: m68k — push Bconout(3) to OUT, drain IN into Iorec
status: todo
milestone: alpha-mvp
---

## Goal

Re-point the EPIC-01 hooks from the local echo to the rings: the `Bconout(3)`
hook pushes each captured byte into the **OUT ring** (instead of straight to
`Iorec`), and a consumer drains the **IN ring** into the `Iorec` input buffer.

## Tasks

- [ ] OUT push helper (advance head, wrap, drop/back-pressure on full) — called from the Bconout(3) hook
- [ ] IN drain: pop available bytes from the IN ring and inject them into the Iorec buffer (the STORY-01/EPIC-01 advance-first inject)
- [ ] Choose where IN is drained — vsync poll in `check_commands`, and/or on the Bconstat/Bconin path — so injected bytes appear promptly
- [ ] `Bcostat(3)` reflects OUT-ring space (back-pressure) instead of always-ready

## Acceptance

The local echo is gone: bytes leave via the OUT ring and arrive via the IN ring,
and (with the RP echo of STORY-03) MIDI Maze still becomes MASTER and plays solo.
No byte loss or lockup when a ring saturates.

## Notes

Keep helpers tiny — they run inside the trap handlers within the 6 KB `userfw`
budget. This replaces the EPIC-01 STORY-04 local echo; the injection mechanics
(Iorec advance-first) are reused unchanged.
