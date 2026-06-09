---
id: STORY-03
epic: EPIC-03
title: Network receive → fill the IN ring
status: todo
milestone: alpha-mvp
---

## Goal

Replace the IN side of EPIC-02's RP-local echo: instead of filling the IN ring
from the drained OUT bytes, fill it from bytes arriving from the orchestrator,
for the m68k to inject into the `Iorec` buffer.

## Tasks

- [ ] Receive callback feeds bytes into the IN ring
- [ ] Drop/handle gracefully when the IN ring is full (and log it)
- [ ] Strip transport framing if a framed protocol was chosen in STORY-01

## Acceptance

Bytes from the orchestrator are delivered to the ST in order (read from the
`Iorec` buffer); an overrun is handled without crashing and is observable in
status.

## Notes

Together with STORY-02 this turns EPIC-02's RP-local echo (STORY-03 there) into a
network exchange; the m68k IN-ring → `Iorec` path (EPIC-02 STORY-02) is unchanged.
