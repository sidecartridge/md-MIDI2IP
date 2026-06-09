---
id: STORY-03
epic: EPIC-03
title: Network receive → the RP IN queue
status: todo
milestone: alpha-mvp
---

## Goal

Replace EPIC-02's local echo on the receive side: bytes arriving from the
orchestrator over TCP do `midi_in_push(byte)`, filling the same RP IN queue that
`CMD_MIDI_RECV` already drains into the shared buffer for the m68k to inject into
`Iorec`.

## Tasks

- [ ] lwIP receive callback feeds incoming bytes into the IN queue (`midi_in_push`)
- [ ] Handle a full IN queue gracefully (drop + log) — the m68k drains it on `CMD_MIDI_RECV`
- [ ] No MIDI parsing — opaque bytes straight into the queue (D-02)

## Acceptance

Bytes the orchestrator (or echo peer) sends are delivered to the ST in order —
queued by the receive callback, drained by `CMD_MIDI_RECV`, read from `Iorec`. A
queue overrun is handled without crashing and is observable in status.

## Notes

Together with STORY-02, this turns the EPIC-02 RP-local echo into a network
exchange. The IN queue and the m68k `CMD_MIDI_RECV` → `Iorec` path are unchanged
from EPIC-02 — only the *producer* of the IN queue changes (echo → network).
