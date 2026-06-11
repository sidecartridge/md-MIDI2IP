---
id: STORY-05
epic: EPIC-06
title: Status screen — Wi-Fi + local IP + orchestrator connection only
status: done
---

## Goal

Strip the on-screen status down to only what matters at a glance — remove the
other parameters currently shown and display just **Wi-Fi status**, the device's
**local IP address**, and the **orchestrator connection status**.

## Tasks

- [x] Remove the extra parameters from the status/menu screen, keeping only the three below
- [x] Show **Wi-Fi status** (down / associating / IP-acquired)
- [x] Show the device's **local IP address** (`network_getCurrentIp`)
- [x] Show the **orchestrator connection status** (down / connecting / up — from the `midi_net_*` state machine, `midi_net_status_str`)
- [x] Render on both the Atari framebuffer and local OLED paths, refreshing live

## Acceptance

The status screen shows only Wi-Fi status, the local IP, and the orchestrator
connection state — all updating live — and nothing else.

## Notes

Wi-Fi/IP come from `network.c` (`network_getCurrentIp`); the orchestrator state
from `midi.c`'s `midi_net_*` state machine (`midi_net_status_str`). Renders
through `display_term` / `term`. Pairs with the boot menu (STORY-02).
