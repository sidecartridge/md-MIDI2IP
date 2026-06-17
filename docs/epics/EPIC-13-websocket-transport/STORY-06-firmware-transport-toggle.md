---
id: STORY-06
epic: EPIC-13
title: Microfirmware transport toggle (config + boot menu)
status: done
---

## Goal

The user picks the transport in the boot menu. It persists across reboots, and the
active transport shows in the status line.

## Tasks

- [x] Add the aconfig keys `MIDI_TRANSPORT` (string `tcp` / `ws`, default `tcp`), `MIDI_WS_PORT` (int, default 5006, since the orchestrator's TCP and WS listeners bind different ports), and `MIDI_WS_PATH` (string, default `/`) in `rp/src/include/midi.h` and the `aconfig.c` defaults
- [x] Read it in `midi_load_config` (`midi.c:475-494`) into a transport-mode variable the connect path consumes
- [x] Add a `[T]ransport` toggle to the boot menu (`emul.c:160-186`) next to `[H]ost` / `[P]ort`, cycling `tcp` / `ws`, saving via `settings_put_string` + `settings_save`, and applying with `midi_net_reload` (mirroring `cmdHost` / `cmdPort`, `emul.c:217-260`). `[P]ort` shows and edits the active carrier's port (`MIDI_PORT` for tcp, `MIDI_WS_PORT` for ws) via `midi_net_port_key()`
- [x] Show the active transport in the status line and the ping output (`midi_net_status_str` / `midi_net_ping`, `midi.c:371-396`)
- [x] Confirm the value survives a power cycle and a live change reconnects with the new transport

## Acceptance

The menu toggles `tcp` / `ws`, the choice persists across a reboot, the status screen
shows the active transport, and changing it live reconnects over the new transport.

## Notes

Config and menu plumbing mirrors EPIC-06. Pairs with STORY-05 (the client that consumes
the mode). The default `tcp` keeps every existing install unchanged.
