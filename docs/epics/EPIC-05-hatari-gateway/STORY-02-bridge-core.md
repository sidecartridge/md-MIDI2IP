---
id: STORY-02
epic: EPIC-05
title: Bridge core (OUT fifo → orchestrator; orchestrator → IN fifo)
status: in-progress
milestone: alpha-mvp
---

## Goal

The byte pump: stream bytes from Hatari's OUT fifo to the orchestrator, and bytes
from the orchestrator to Hatari's IN fifo — the software equivalent of the RP byte
pipe. Byte-dumb (D-02).

## Tasks

- [x] `bridge()` reads the Atari-OUT fifo and `sendall`s to the orchestrator socket (the `CMD_MIDI_SEND` analogue)
- [x] Reads the orchestrator socket and `os.write`s to the Atari-IN fifo (the `CMD_MIDI_RECV` / Iorec analogue)
- [x] Both directions in one `select()` loop (single-thread, stdlib) — readiness-driven so neither blocks the other
- [x] Verbatim, in order, no parsing (D-02); `TCP_NODELAY` + immediate writes for latency (C-01)

## Acceptance

A byte written to the OUT fifo reaches the orchestrator, and a byte from the
orchestrator appears on the IN fifo — byte-exact, in order, low latency, both
directions at once.

## Notes

Mirrors `midi.c`: OUT fifo = the m68k OUT path, IN fifo = the RP IN queue → Iorec.
No MIDI Maze awareness. Pick the concurrency model that keeps both directions live
(an asyncio loop reading the fifo via an executor or a non-blocking fd, or a
two-thread design) — all stdlib.
