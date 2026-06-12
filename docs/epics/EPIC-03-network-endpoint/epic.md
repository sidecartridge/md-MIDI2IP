---
id: EPIC-03
iteration: 1
title: RP network endpoint
status: done
---

## Goal

Move the loopback one more layer out: replace EPIC-02's **RP-local echo** with a
**network exchange to the orchestrator**. The change is entirely RP-side, at one
seam in `rp/src/midi.c`:

- `CMD_MIDI_SEND`: instead of `midi_in_push(byte)` (the local echo), **send the
  byte to the orchestrator**.
- a **network-receive** path: bytes arriving from the orchestrator do
  `midi_in_push(byte)`, filling the same IN queue that `CMD_MIDI_RECV` already
  drains into the shared buffer.

The m68k side and the byte-pipe protocol (`CMD_MIDI_SEND`/`CMD_MIDI_RECV`,
`MIDI_IN_*`) are unchanged. The RP becomes a TCP client to the orchestrator.

## Scope

- In scope (RP side): the TCP connection lifecycle, sending OUT bytes, receiving
  bytes into the IN queue, reconnect/link status, a liveness ping, and validating
  the network round-trip.
- Out of scope: the **orchestrator** (EPIC-04, in this repo), which wires the ring
  and is what makes real gameplay possible (D-09). Config source is EPIC-06; wire
  format is already decided (raw bytes / TCP, D-02/D-03).

## Two validation levels (D-09)

- **Network plumbing (in this epic):** with a trivial desktop **echo peer**, the
  MIDI Maze handshake round-trips over the wire (master election + COUNT-PLAYERS +
  config), exactly as EPIC-02 but networked. That's STORY-05 here.
- **Gameplay (needs the orchestrator):** MIDI Maze won't start a match without a
  real 2nd node (D-09). That requires the orchestrator (EPIC-04) to wire a ring,
  with the 2nd node a 2nd ST or a Hatari gateway player (EPIC-05), not RP
  firmware. Tracked in those epics, not as an EPIC-03 RP story.

## Stories

- STORY-01: Connection lifecycle to the orchestrator
- STORY-02: Send OUT bytes to the orchestrator (replace the echo)
- STORY-03: Network receive → the RP IN queue
- STORY-04: Error handling, reconnect, link status
- STORY-05: Validate the network round-trip (echo peer)
- STORY-06: Endpoint liveness ping command
- STORY-07: Remove unused HTTP/HTTPS/TLS plumbing

## Notes

Use the existing `network.c` / lwIP poll-mode plumbing. The RP is a TCP client to
the orchestrator; raw byte stream over TCP + `TCP_NODELAY` (D-02/D-03). Keep the
Keep the RP protocol-dumb; all MIDI-Maze awareness lives in the orchestrator.
