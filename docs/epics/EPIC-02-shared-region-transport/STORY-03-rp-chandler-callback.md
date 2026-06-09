---
id: STORY-03
epic: EPIC-02
title: RP — drain the OUT ring and echo it into the IN ring
status: todo
milestone: alpha-mvp
---

## Goal

Move the echo into the RP. Extend the MIDI `chandler` callback so that, each
`chandler_loop` iteration, it drains the OUT ring and writes those bytes into the
IN ring — the same "ring of one" as EPIC-01, but now closed on the RP side. This
is the boundary EPIC-03 later cuts to insert the network.

## Tasks

- [ ] Add OUT-drain / IN-fill to the MIDI callback in `rp/src/midi.c` (already registered via `chandler_addCB`)
- [ ] Echo: drained OUT bytes → IN ring (the RP-local loopback; later replaced by the network send/recv)
- [ ] Respect IN-ring fullness; never overrun
- [ ] Keep it non-blocking — the PIO bus loop runs hot (225 MHz); bound per-iteration work

## Acceptance

With the m68k ring I/O (STORY-02), bytes the ST sends come back through the rings
via the RP echo, and MIDI Maze still becomes MASTER and plays solo — now with the
echo proven to live in the RP (visible on the serial console).

## Notes

`midi_command_cb` already exists (`rp/src/midi.c`) and is registered in
`emul_start()`. The echo here is the explicit hand-off point for EPIC-03: swap
"OUT → IN" for "OUT → network → IN".
