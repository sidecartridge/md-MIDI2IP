---
id: STORY-01
epic: EPIC-15
title: Flush the firmware OUT queue and reset link state on a drop
status: done
---

## Goal

A link drop leaves no firmware-side bytes that a reconnect could replay.

## Tasks

- [x] Flush the OUT ring in `midi_net_reset` (set `midiOutTail = midiOutHead`) so queued `Bconout` bytes from before a drop are not sent on the next connection. Today only the IN queue is flushed; the OUT queue waits for the 1 s stale cleanup, so a reconnect inside that window replays pre-drop bytes
- [x] Reset the WS receive state on a drop (re-init the frame decoder and the handshake accumulator) so a reconnect starts clean, rather than relying on `start_handshake` to re-init
- [x] Confirm the IN ack and the published `MIDI_IN_STATUS` are reset so `Bconstat` reports no byte after a drop (already via `midi_net_flush_in_queue`; verify)
- [x] Re-stamp the OUT/IN staleness timestamps on reset so the cleanup logic stays consistent
- [x] Build clean (`pico_w`) and note any flash delta

## Acceptance

After a link drop, both the IN and OUT queues are empty and the WS receive state is fresh,
so a reconnect cannot replay pre-drop bytes. `pico_w` build clean.

## Notes

`midi_net_reset` (`rp/src/midi.c`) currently calls only `midi_net_flush_in_queue`. The OUT
ring is `midiOutQueue` / `midiOutHead` / `midiOutTail`. Keep the hot path untouched; this
is all in the reset path (poll/callback context).
