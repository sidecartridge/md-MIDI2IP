---
id: EPIC-08
title: Match coordination (smart orchestrator)
status: todo
---

## Goal

Make a real **MIDI Maze match playable** over the orchestrator. Transport,
latency and protocol visibility are solved (EPIC-01..05): bytes flow byte-exact,
the `BUS_LOOP_MS` fix cut per-byte latency ~100×, and `--inspect` decodes the
ring traffic. But hardware testing surfaced two **protocol-level** blockers a
byte-dumb relay (D-10) cannot fix:

1. **Master election doesn't converge** with asynchronously-launched machines.
   Multiple nodes auto-elect; a SLAVE re-sends every `0x00` (Anexo A), so with no
   single master the election byte loops forever and re-triggers mid-COUNT —
   the MASTER reads a garbage/zero player count and never starts (D-11).
2. **The ~4 KB `SEND-DATA` maze (`0x83`) overflows the RP's IN path** when it
   circulates the ring, losing bytes exactly at "start game" (D-11).

This epic adds the **protocol-aware coordination layer** — the "later smart
epic" named in D-09/D-10 — built on the `--inspect` decoder. It lives in the
**orchestrator** (plus RP buffer work for flow-control) and is **gated behind a
flag** so the dumb ring relay stays the default (D-02/D-10).

## Scope

- **In:** a stateful per-ring protocol model (built on the `--inspect` decoder);
  a **master-election coordinator** (exactly one stable master, launch-order
  proof); **ring flow-control** for large messages (SEND-DATA); end-to-end
  validation of a full 2-player match.
- **Out:** game-session UI/stats ("gameplays disputing/disputed", D-10) beyond
  what the model needs; keeping the RP/byte-pipe dumb (D-02) — **all** protocol
  awareness lives in the orchestrator; drones / >2 players (post-MVP, D-04).

## Stories

- STORY-01 — Ring protocol-state model (stateful, authoritative — built on `--inspect`)
- STORY-02 — Master-election coordinator (one stable master, any launch order)
- STORY-03 — Ring flow-control: survive the ~4 KB SEND-DATA without loss
- STORY-04 — Validate: a full 2-player MIDI Maze match starts and plays

## Notes

Born from the EPIC-05 hardware session (D-11). The orchestrator's `--inspect`
`MidiMazeInspector` is the read-only foundation; this epic makes it authoritative
and lets the orchestrator *act* on it. The coordinator is the first place the
orchestrator stops being byte-dumb (D-02) — gated, opt-in, orchestrator-only.
References: D-02 (dumb pipe, now selectively relaxed in the orchestrator behind a
flag), D-04 (ring stable before a game), D-09/D-10 (the smart epic), C-01
(lock-step / latency), D-11 (the two blockers).
