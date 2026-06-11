---
id: STORY-03
epic: EPIC-03
title: Network receive → the RP IN queue
status: done
milestone: alpha-mvp
---

## Goal

Replace EPIC-02's local echo on the receive side: bytes arriving from the
orchestrator over TCP do `midi_in_push(byte)`, filling the same RP IN queue that
`CMD_MIDI_RECV` already drains into the shared buffer for the m68k's `Bconin(3)`
to return.

## Tasks

- [x] lwIP `tcp_recv` callback walks the pbuf chain and feeds bytes into the IN queue (`midi_in_push`)
- [x] Full IN queue drops gracefully (`midi_in_push` no-ops when full); the m68k drains it on `CMD_MIDI_RECV`
- [x] No MIDI parsing — opaque bytes straight into the queue (D-02)

## Acceptance

Bytes the orchestrator (or echo peer) sends are delivered to the ST in order —
queued by the receive callback, drained by `CMD_MIDI_RECV`, read via `Bconin`. A
queue overrun is handled without crashing and is observable in status.

**Verified on hardware:** the echo peer's echoed bytes arrive back at the ST and
drive master election over the network.

## Notes

Together with STORY-02, this turns the EPIC-02 RP-local echo into a network
exchange. The IN queue and the m68k `CMD_MIDI_RECV` → `Bconin` path are unchanged
from EPIC-02 — only the *producer* of the IN queue changes (echo → network).
