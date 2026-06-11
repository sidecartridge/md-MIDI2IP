---
id: STORY-02
epic: EPIC-06
title: Boot menu with countdown (E = firmware, X = Booster)
status: done
---

## Goal

Replace the ad-hoc command flow with a **boot menu** modelled on
md-drives-emulator: on launch the app shows a menu screen with a **countdown**;
the user presses **E** to start the MIDI-to-IP firmware (the m68k `userfw` hook)
or **X** to jump to the Booster, and when the countdown reaches zero it
auto-starts the firmware.

## Tasks

- [x] Render a boot-menu screen (Atari framebuffer + local OLED) with the app name, the key hints, and a live **countdown** — porting md-drives-emulator's menu/countdown rendering (`term` / `display_term`)
- [x] **[E]** starts the MIDI-to-IP firmware: triggers the existing `f`/`CMD_START` → `rom_function` → `USERFW` dispatch and tears the menu down
- [x] **[X]** jumps to the Booster via `reset_jump_to_booster()` (already in `reset.c`), mirroring md-drives-emulator's exit-to-Booster
- [x] The countdown auto-runs the **[E]** action on expiry; any keypress before zero cancels the auto-start
- [x] Only E / X act; all other keys are ignored on the menu

## Acceptance

On boot the menu appears with a counting-down timer; pressing **E** (or letting
the countdown finish) launches the MIDI firmware; pressing **X** boots the
Booster. Look and behaviour mirror md-drives-emulator.

## Notes

Port md-drives-emulator's boot-menu code (countdown + E/X handling) into this
app's terminal stack (`term.c` / `display_term.c` / the `emul.c` main loop). The
firmware-launch action already exists as the `f` ([F]irmware) dispatch; the
Booster action is `reset_jump_to_booster()`. The endpoint input screens (STORY-04)
and the minimal status screen (STORY-05) hang off this menu.
