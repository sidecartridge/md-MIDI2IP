---
id: EPIC-15
iteration: 6
title: Robustness pass (buffer cleanup on disconnect)
status: done
---

## Goal

The solution plays MIDI Maze reliably most of the time, but stale bytes can survive a
connection drop. The firmware clears its IN queue on a link reset but not its OUT queue, so
a reconnect inside the staleness window can replay pre-drop bytes. This epic tightens buffer
cleanup on every side so a drop leaves nothing queued: the firmware flushes both queues and
resets its link state, and the orchestrator and the gateway are confirmed to hold no queued
or buffered data (including partial frames) once a connection closes.

## Scope

- In scope: flush the firmware OUT queue and reset the WS and IN state on a link drop;
  confirm the orchestrator and the gateway discard all queued and buffered data, including
  partial frames, on disconnect; tests plus a hardware re-validation of the reconnect
  scenarios.
- Out of scope: changing the dumb-relay model (D-02); `wss` / TLS; MIDI-Maze-aware
  orchestrator logic (D-09).

## Stories

- STORY-01: Flush the firmware OUT queue and reset link state on a drop
- STORY-02: Confirm the orchestrator and gateway drop everything on disconnect
- STORY-03: Validate the robustness fixes on hardware

## Notes

Grounded by D-02 (dumb byte pipe), D-04 (ring routing), C-01 (lock-step). The firmware OUT
queue gap is in `midi_net_reset` (`rp/src/midi.c`), which flushes only the IN queue today,
so a reconnect within the 1 s stale window replays queued OUT bytes.
