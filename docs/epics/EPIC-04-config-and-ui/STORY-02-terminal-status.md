---
id: STORY-02
epic: EPIC-04
title: Status command and config editing (terminal + serial)
status: todo
---

## Goal

Provide the `status` command — a single place that reports link state, byte
counters, and current config — rendered on the terminal and emitted in a
machine-readable form over the serial console, plus a way to edit the endpoint
settings.

## Tasks

- [ ] Add a `status` command to the terminal menu reporting link state, host:port, transport, uptime, OUT/IN byte counters, ring usage, last error
- [ ] Emit the same status in a machine-readable line over the serial debug console
- [ ] Allow editing endpoint host/port/transport/enabled from the terminal
- [ ] Render on both the Atari framebuffer and local OLED paths

## Acceptance

`status` shows live counters that move when MIDI flows and reflects the real
connection state; the serial form is parseable; edits take effect and persist
(via EPIC-04 STORY-01).

## Notes

Hook into `term.c` / `display_term.c`; served via `term_command_cb`. This is the
single home for status reporting — the EPIC-03 STORY-06 `ping` command surfaces
its result here too.
