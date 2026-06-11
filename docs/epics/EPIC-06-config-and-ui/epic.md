---
id: EPIC-06
iteration: 1
title: Configuration, UI & template cleanup
status: done
---

## Goal

Give the device its own UI — a boot menu, on-screen input for the orchestrator
endpoint, and a minimal live status — persist the config in per-app flash, and
strip the codebase down to only what MIDI-to-IP actually uses (the app started
from the Sidecartridge template). Modelled on md-drives-emulator's menu/config UI.

## Scope

- In scope: per-app config keys (endpoint host, port, enable) on top of
  `aconfig`; a md-drives-emulator-style **boot menu** (countdown, E = firmware,
  X = Booster); **input screens** for the orchestrator host + port (reusing
  md-drives-emulator's RTC hostname/port screens); a **minimal status screen**
  (Wi-Fi, local IP, orchestrator connection); and removing unused template/demo
  code, including the **SD-card subsystem**.
- Out of scope: the actual networking (EPIC-03) and hooking (EPIC-01).

## Stories

- STORY-01 — Per-app config keys for the MIDI endpoint
- STORY-02 — Boot menu with countdown (E = firmware, X = Booster)
- STORY-03 — Trim the template + remove the SD-card subsystem
- STORY-04 — Input screens for the orchestrator endpoint (host/IP + port)
- STORY-05 — Status screen — Wi-Fi + local IP + orchestrator connection

## Notes

Use `aconfig.c` (per-app config in `CONFIG_FLASH`). The UI lives in the terminal
stack (`term.c` / `display_term.c`); the boot menu and the endpoint input screens
are ports of md-drives-emulator's menu + RTC-config screens, and the Booster jump
is `reset_jump_to_booster()` (`reset.c`).
