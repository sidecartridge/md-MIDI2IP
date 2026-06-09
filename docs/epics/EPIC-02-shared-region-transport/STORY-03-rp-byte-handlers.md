---
id: STORY-03
epic: EPIC-02
title: RP — byte queues + OUT→IN echo (CMD_MIDI_SEND/RECV handlers)
status: todo
milestone: alpha-mvp
---

## Goal

Handle the two commands in `rp/src/midi.c` with two opaque byte queues, and close
the loopback on the RP by echoing OUT into IN. App-agnostic — just bytes.

## Tasks

- [ ] `CMD_MIDI_SEND`: read the byte(s) from the command payload and enqueue them (OUT queue)
- [ ] Echo: move OUT-queue bytes into the IN queue (the RP-local loopback; later replaced by the network)
- [ ] `CMD_MIDI_RECV`: drain the IN queue into the shared `MIDI_IN_BUFFER`, write `MIDI_IN_COUNT`, then let chandler bump the token (like GEMDRIVE `READ_BUFFER`)
- [ ] Keep both handlers non-blocking and bounded — the bus loop runs hot (225 MHz)

## Acceptance

OUT bytes the ST sends come back through `CMD_MIDI_RECV`, and solo MIDI Maze still
becomes MASTER and plays — with the echo proven to live in the RP (SEND/RECV
counts visible on the serial console).

## Notes

`midi_command_cb` already exists and is registered. The OUT→IN echo here is the
explicit seam for EPIC-03: replace "echo OUT into IN" with "send OUT to the
orchestrator / fill IN from it".
