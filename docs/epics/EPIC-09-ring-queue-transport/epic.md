---
id: EPIC-09
iteration: 2
title: Change command transport to ring-queue device communications
status: todo
---

## Goal

Replace the per-byte m68k↔RP **command handshake** (D-12) with shared-memory
**ring-queue** communication in the cartridge window, so MIDI throughput beats the
physical MIDI ring instead of being ~3× slower. Today every MIDI byte is a full
`send_sync` command (~0.5 ms round-trip, measured ~970 bytes/s); a ring buffer the
m68k reads/writes **directly** — each side owning its own index — removes the
per-byte handshake entirely, leaving the bus and Wi-Fi as the only limits.

## Scope

- **In:** IN/OUT ring buffers in the shared region with a producer index and a
  consumer index; the m68k BIOS hook (`Bconin`/`Bconstat`/`Bconout`) reads/writes
  the rings directly with **no command per byte**; the RP fills the IN ring from
  the network and drains the OUT ring to it; the **m68k-side RAM** needed to hold
  its own ring index (cartridge code is ROM, so this is the crux); flow-control
  when a ring is full.
- **Out:** the network transport (EPIC-03) and orchestrator (EPIC-04) stay as-is;
  MIDI Maze protocol awareness stays in the orchestrator (D-02); re-validating a
  full match and the automated CI gate (the Iteration-1 deferred stories) — those
  resume once this transport lands.

## Stories

_To be defined._

## Notes

Born from **D-12**: the Iteration-1 architecture spike proved the whole stack but
found the per-byte command handshake is the throughput ceiling. The hard part is
**m68k-side mutable state** — cartridge code runs from ROM, so the m68k needs a
few bytes of system RAM (or a reserved scratch) to hold its ring read/write index;
`Bconstat` already reads a shared longword without a command, which is the model
to generalise. References: D-12 (the flaw + fix direction), D-02 (dumb byte pipe),
C-01 (lock-step latency budget), EPIC-01 (the BIOS hook), EPIC-02 (the shared
region this builds on).
