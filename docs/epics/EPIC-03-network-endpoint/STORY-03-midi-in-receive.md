---
id: STORY-03
epic: EPIC-03
title: Network receive → MIDI IN bytes
status: todo
milestone: alpha-mvp
---

## Goal

Take bytes arriving from the remote endpoint and push them into the IN ring for
the m68k `Bconin` hook to deliver.

## Tasks

- [ ] Receive callback feeds bytes into the IN ring
- [ ] Drop/handle gracefully when the IN ring is full (and log it)
- [ ] Strip transport framing if a framed protocol was chosen in STORY-01

## Acceptance

Bytes sent by the remote peer are delivered to the ST in order via `Bconin`; an
overrun is handled without crashing and is observable in status.

## Notes

Pairs with EPIC-01 STORY-04 and EPIC-02 STORY-03.
