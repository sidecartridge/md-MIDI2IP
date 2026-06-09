---
id: EPIC-04
title: Configuration, UI & template cleanup
status: todo
---

## Goal

Let the user configure the remote endpoint and behaviour, persist it in per-app
config, view live status from the terminal — and strip the codebase down to only
what MIDI-to-IP actually uses (the app started from the Sidecartridge template).

## Scope

- In scope: per-app config keys (endpoint host, port, transport, enable,
  pass-through-to-physical-port) on top of `aconfig`, a terminal command to view
  status and edit settings, and removing unused template/demo code.
- Out of scope: the actual networking (EPIC-03) and hooking (EPIC-01).

## Stories

- STORY-01 — Per-app config keys for the MIDI endpoint
- STORY-02 — Terminal command to view status and edit config
- STORY-03 — Trim the microfirmware template of unused code

## Notes

Use `aconfig.c` (per-app config in `CONFIG_FLASH`). The terminal stack is
`term.c` / `display_term.c`; add the command alongside the existing ones served
through `term_command_cb`.
