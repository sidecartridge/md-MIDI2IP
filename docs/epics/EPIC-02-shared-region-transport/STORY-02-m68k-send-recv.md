---
id: STORY-02
epic: EPIC-02
title: m68k — ship OUT via CMD_MIDI_SEND; pull IN via CMD_MIDI_RECV → Bconin
status: done
milestone: alpha-mvp
---

## Goal

Wire the m68k side of the byte pipe into the EPIC-01 hooks, replacing the local
echo. The two directions are independent.

## Tasks

- [x] OUT: the `Bconout(3)` hook ships the captured byte via `send_sync CMD_MIDI_SEND`, then chains and returns — no readback
- [x] IN: issue `CMD_MIDI_RECV`, read `MIDI_IN_COUNT` + copy `MIDI_IN_BUFFER`, and deliver those bytes via `Bconin`/`Bconstat`
- [x] Pick the IN-pull cadence — the vsync `check_commands` loop and/or the `Bconstat(3)` path — so injected bytes appear promptly without flooding the command channel
- [x] Remove the EPIC-01 local echo

## Acceptance

With the RP echo (STORY-03), the local echo is gone yet solo MIDI Maze still
becomes MASTER and plays — bytes leave via `CMD_MIDI_SEND` and arrive via
`CMD_MIDI_RECV` → `Bconin`.

## Notes

`send_sync` from inside the `Bconout` trap is the proven pattern (md-drives-emulator
does sector I/O this way). The pull cadence interacts with the open readback-timing
question (D-05): if MIDI Maze's read blocks, a vsync pull is fine; if it
polls-once, the pull must be tied closer to `Bconstat(3)`. Settle this during
bring-up; it's a tuning knob, not a protocol change.
