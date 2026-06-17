---
id: STORY-09
epic: EPIC-14
title: Firmware room key (config + boot menu + Bearer handshake header)
status: todo
---

## Goal

The user types a room key on the firmware menu; it persists and rides the WebSocket
handshake as `Authorization: Bearer`.

## Tasks

- [ ] Add the aconfig key `MIDI_ROOM` (string, default empty = default room) in `rp/src/include/midi.h` and the `aconfig.c` defaults
- [ ] Read it in `midi_load_config` into a room variable, normalized to uppercase
- [ ] Add a `[R]oom` boot-menu entry (DATA_INPUT, like `[H]ost`) to type and persist the key; apply via `midi_net_reload`; show the room in the menu and the status line
- [ ] Include `Authorization: Bearer <room>` in the WS client handshake (`midi_ws_start_handshake`) when a room is set; omit it for the default room
- [ ] Note in the menu that the room applies on the `ws` transport; a `tcp` node uses the default room
- [ ] Build clean (`pico_w`) and confirm the key persists across a power cycle

## Acceptance

The menu accepts a room key, it persists across a reboot, and a `ws` node joins that room
(visible under that room in the orchestrator). An empty key uses the default room.

## Notes

Pairs with STORY-02 / STORY-03 (the orchestrator routing and provisioning). The boot-menu
plumbing mirrors `[H]ost` / `[P]ort` (EPIC-06) and the `[T]ransport` toggle (EPIC-13
STORY-06). The handshake header reuses the EPIC-13 WS client.
