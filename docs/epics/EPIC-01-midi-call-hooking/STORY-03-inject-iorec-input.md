---
id: STORY-03
epic: EPIC-01
title: Deliver MIDI input to Bconin(3)/Bconstat(3)
status: done
milestone: alpha-mvp
---

> **Superseded:** this story delivered input by injecting into the system
> `Iorec(2)` buffer. The BIOS hook now serves `Bconin`/`Bconstat` **directly**
> from the RP queue — no Iorec at all (D-05). The body below is the original
> record.

## Goal

Deliver bytes to MIDI Maze by writing them into the **system MIDI input record**
(`Iorec(2)`). Both `Bconin(3)` and the XBIOS readback consume that buffer, so
feeding it serves every read path MIDI Maze uses — without us having to know
which one it picks (resolves the D-05 input question in practice).

## Tasks

- [x] Cache the MIDI `Iorec(2)` record pointer at install (patched into the served ROM via the RP handshake)
- [x] Inject a byte the way TOS does: advance the head, then store at the new head
- [x] Drop on overflow (head would meet the tail)
- [x] Confirm `Bconstat(3)` then reports ready and the byte is read back (Bconin / the readback)

## Acceptance

A byte injected into the Iorec buffer is seen as "received" by the ST: `Bconstat`
reports it, and a read returns it in order. Confirmed on hardware via the loopback
(STORY-04).

## Notes

The advance-first ordering matters — TOS readers advance the tail then read at the
new tail, so storing then advancing would be off by one. There's no read path to
hook directly: populating the shared `Iorec` buffer covers Bconin *and* the XBIOS
readback at once.
