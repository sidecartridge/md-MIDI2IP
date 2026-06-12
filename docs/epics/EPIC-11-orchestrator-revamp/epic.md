---
id: EPIC-11
iteration: 2
title: Orchestrator revamp — dumb relay + ring observability
status: done
---

## Goal

Now that the firmware owns the MIDI ring end-to-end (EPIC-09 — election, COUNT,
SEND-DATA all run over the commemul fast path), the orchestrator no longer needs to
model the protocol to do its job: it just relays bytes. Simplify it back to a **dumb
relay** (keeping the `--inspect` decoder for debugging) and give it real
**observability** — a live in-browser ring visualization showing each node's host/IP
and byte counters, plus reverse-DNS naming and clean node recycling on reconnect.

## Background

The orchestrator (`orchestrator/orchestrator.py`) today carries an EPIC-08
protocol-state model (`RingState` + per-player `MidiMazeInspector` decoders) that
heuristically tracks master election / COUNT / phases. With the firmware now driving
the ring correctly, that model is no longer load-bearing — it was a heuristic (it
caused a master-flip on hardware, D-04) and maintaining it is dead weight + a source
of drift. The read-only `MidiMazeInspector` behind `--inspect` stays: a decoder you
can switch on to watch a session is still the right tool.

The HTTP surface (`_status_snapshot` / `_status_json` / `_status_html`) becomes a
proper telemetry feed + a real visualization instead of a static HTML dump.

## Scope

- **In:** retire `RingState` (the stateful ring model) → pure byte relay; keep
  `--inspect`; per-node telemetry in `status.json` (IP, reverse-DNS host, bytes
  in/out, ring order); a revamped self-contained HTML page that draws the ring and
  polls `status.json` every 2 s; reconnection node recycling (supersede a stalled
  prior same-IP connection, recycling the node id).
- **Out:** the firmware/RP side (EPIC-09, done); the wire transport; MIDI-protocol
  awareness beyond `--inspect` (D-02 — the relay stays opaque); auth and multi-ring
  (the single global ring stays).

## Stories

- **STORY-01** Retire the protocol-state model → dumb relay (keep `--inspect`)
- **STORY-02** Reconnection node recycling (supersede a stalled prior same-IP connection)
- **STORY-03** Reverse-DNS the connected node hostnames
- **STORY-04** Per-node telemetry in `status.json` (IP, host, bytes in/out)
- **STORY-05** Revamped ring-visualization HTML page (polls `status.json` every 2 s)

## Constraints (must preserve)

- The relay stays **opaque** — raw bytes, order preserved, no parsing on the relay
  path (D-02). Decoding happens only in the off-path `--inspect` decoder.
- Single asyncio loop; status reads stay race-free (snapshot from the loop, as today).
- Reverse-DNS and the HTTP page must never block or add latency to the relay.
- HTML page is self-contained (no external/CDN deps) — served by the existing
  asyncio HTTP, offline-friendly.

## Notes

Enabled by EPIC-09 (the firmware now owns the ring). Touches only
`orchestrator/orchestrator.py` and its served HTML/JSON. Reference: EPIC-04 (the
relay this returns to), EPIC-08 (the `RingState` coordination being retired), EPIC-04
STORY-04 (the one-connection-per-IP dedup that STORY-02 extends).
