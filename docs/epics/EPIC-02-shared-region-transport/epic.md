---
id: EPIC-02
iteration: 1
title: MIDI byte transport (m68k ↔ RP)
status: done
---

## Goal

Move the loopback from the Atari (EPIC-01) to the **RP**, over a dumb,
app-agnostic **byte pipe** built on the SidecarTridge command protocol. The pipe
just moves raw bytes both ways and knows nothing about MIDI Maze (master
election, lock-step, the ring all stay in the game + the orchestrator). The same
solo game still becomes MASTER and plays — but the bytes now cross to the RP,
which is where EPIC-03 inserts the network.

This respects the hardware: **$FA0000 (ROM4) and $FB0000 (ROM3) are ROM**, so the
m68k can only *read* them and owns no shared-region state. The two directions:

- **OUT** (m68k → RP): the `Bconout(3)` hook ships the byte via a command
  (`CMD_MIDI_SEND`, ROM3-read addressing — like GEMDRIVE `Fwrite`), then chains
  and returns. No readback.
- **IN** (RP → m68k): the m68k pulls pending bytes via `CMD_MIDI_RECV`; the RP
  writes them into a shared buffer + count that appear as ROM, the m68k reads
  them and delivers them to `Bconin` (from the RP IN queue) — like GEMDRIVE's
  `READ_BUFFER`/`READ_BYTES` pattern.

The RP echoes OUT→IN (the loopback now lives in the RP); EPIC-03 swaps the echo
for the network.

## Scope

- In scope: the `CMD_MIDI_SEND`/`CMD_MIDI_RECV` commands, the shared IN buffer
  layout, the m68k send/recv wiring into the EPIC-01 hooks, and the RP byte
  queues + echo.
- Out of scope: the OS-call interception (EPIC-01) and the network (EPIC-03). The
  pipe carries opaque bytes; no MIDI semantics live here.

## Stories

- STORY-01 — Define the byte-pipe protocol + shared IN buffer
- STORY-02 — m68k: ship OUT via CMD_MIDI_SEND; pull IN via CMD_MIDI_RECV → Bconin
- STORY-03 — RP: byte queues + OUT→IN echo (CMD_MIDI_SEND/RECV handlers)
- STORY-04 — Validate: solo MIDI Maze over the byte pipe

## Notes

Builds on a completed EPIC-01. The m68k owns **no** state in $FA/$FB — the RP
writes all shared buffers, the m68k reads them and keeps its own position in ST
RAM. Modeled directly on md-drives-emulator's `Fread`/`Fwrite`.
