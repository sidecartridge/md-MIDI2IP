---
id: EPIC-05
title: Hatari gateway
status: todo
---

## Goal

A **software RP2040** for the [Hatari](https://www.hatari-emu.org/) emulator.
Hatari can route the Atari's raw MIDI to/from files; this gateway bridges those
files to the **orchestrator** (EPIC-04), so **MIDI Maze running in Hatari becomes a
virtual player** — no hardware needed. Lives in its own folder `hatari-gateway/`,
**Python 3 standard library only** (no third-party packages).

This is the project's **test peer**: it replaces the old "desktop test peer"
idea. A Hatari instance + this gateway is indistinguishable, to the orchestrator,
from a real ST + RP2040 — so you can play/validate the whole stack on a laptop,
and a single real ST can finally get a second node to start a match (D-09).

## Scope

- **In:** create/manage the two Hatari MIDI FIFOs; the bridge loop (Atari-OUT
  file → orchestrator; orchestrator → Atari-IN file); an orchestrator TCP client
  with reconnect; documentation of the Hatari invocation.
- **Out:** the orchestrator itself (EPIC-04); any MIDI Maze protocol awareness
  (the gateway is byte-dumb, exactly like the RP, D-02).

## Hatari file mechanism

Hatari's flags are counter-intuitively named:
- `--midi-in <file>` — Hatari **writes** the Atari's MIDI **OUT** here (Atari → host).
- `--midi-out <file>` — Hatari **reads** the Atari's MIDI **IN** from here (host → Atari).

For real-time we use two **named pipes (FIFOs)**: the gateway reads the OUT fifo
and writes the IN fifo continuously.

## Stories

- STORY-01 — FIFO setup + documented Hatari invocation
- STORY-02 — Bridge core (OUT fifo → orchestrator; orchestrator → IN fifo)
- STORY-03 — Orchestrator client (connect, reconnect/backoff, status)
- STORY-04 — Validate: Hatari MIDI Maze joins the ring as a player

## Notes

Maps 1:1 onto the RP firmware we built: the OUT fifo is the m68k `CMD_MIDI_SEND`
side, the IN fifo is the `CMD_MIDI_RECV` / Iorec side, and the orchestrator client
mirrors `midi_net_*`. Stdlib-only and FIFO-based keeps it portable and trivially
runnable next to Hatari.
