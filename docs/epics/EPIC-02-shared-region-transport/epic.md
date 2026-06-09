---
id: EPIC-02
title: Shared-region MIDI transport
status: todo
---

## Goal

Move MIDI bytes between the m68k hooks (EPIC-01) and the RP firmware (EPIC-03)
through the 64 KB shared cartridge region, using lock-free ring buffers and the
existing command/sentinel protocol. This is the bridge across the two targets.

## Scope

- In scope: defining the MIDI IN/OUT ring layout in the `APP_FREE` arena (with
  symbolic offsets on both sides), the m68k producer/consumer, and the RP-side
  `chandler` callback that services the rings.
- Out of scope: socket I/O (EPIC-03) and the OS call interception (EPIC-01).

## Stories

- STORY-01 — Define MIDI IN/OUT ring buffers in the shared region
- STORY-02 — m68k producer/consumer with flow control
- STORY-03 — RP chandler callback to drain OUT / fill IN
- STORY-04 — Extend the self-test harness across the real ring transport

## Notes

Layout must live as named constants in `rp/src/include/chandler.h` (RP) and
`target/atarist/src/main.s` (m68k) — never hard-code addresses inside
`$FA0000`–`$FAFFFF`. Use the `APP_FREE` arena at `$FA2300`; keep clear of the
framebuffer at `$FAE0C0`.
