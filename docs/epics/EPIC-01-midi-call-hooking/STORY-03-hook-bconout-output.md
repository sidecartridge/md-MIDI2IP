---
id: STORY-03
epic: EPIC-01
title: Hook BIOS Bconout/Bcostat device 3 (MIDI output)
status: todo
milestone: alpha-mvp
---

## Goal

Intercept single-byte MIDI output via BIOS `Bconout` (and report readiness via
`Bcostat`) for device 3 (MIDI), routing bytes to the OUT ring.

## Tasks

- [ ] Filter trap #13 for `Bconout` with device == 3
- [ ] Push the byte into the MIDI OUT ring
- [ ] Make `Bcostat` device 3 reflect OUT-ring space (back-pressure)
- [ ] Leave other BIOS devices (console, printer, aux) untouched

## Acceptance

Byte-at-a-time MIDI output (e.g. note on/off via `Bconout`) reaches the OUT ring
in order; `Bcostat` blocks the sender when the ring is full rather than dropping.

## Notes

`Bconout(dev, ch)` — dev 3 = MIDI. `Bcostat(dev)` returns -1 ready / 0 not. This
is the MIDI Maze output path (D-05) — the alpha MVP output hook.
