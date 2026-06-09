---
id: EPIC-02
title: Shared-region MIDI ring transport
status: todo
---

## Goal

Move the loopback from m68k-local (EPIC-01) to **RP-mediated**. Route the captured
MIDI through two byte rings in the 64 KB shared region: the m68k pushes each
`Bconout(3)` byte into the **OUT ring** and drains the **IN ring** into the
`Iorec` buffer, while the RP drains OUT and refills IN — so the echo now lives in
the RP instead of the Atari. The visible result is unchanged (solo MIDI Maze still
becomes MASTER and plays), but the data now crosses to the RP. That seam is
exactly where the network plugs in next (EPIC-03 swaps the RP-local echo for the
orchestrator round-trip).

## Scope

- In scope: the OUT/IN ring layout in the shared region (symbolic offsets on both
  sides), the m68k ring producer/consumer wired into the EPIC-01 hooks, the RP
  drain-OUT/echo/fill-IN callback, and flow control / back-pressure.
- Out of scope: the OS-call interception itself (done in EPIC-01) and the network
  (EPIC-03). EPIC-02 keeps the echo local to the RP.

## Stories

- STORY-01 — Define the OUT/IN MIDI ring buffers in the shared region
- STORY-02 — m68k: push Bconout(3) to OUT, drain IN into Iorec (replace the local echo)
- STORY-03 — RP: drain the OUT ring and echo it into the IN ring
- STORY-04 — Validate: solo MIDI Maze via the RP-mediated rings

## Notes

Builds on a **completed EPIC-01** (linear flow). Layout lives as named constants
in `rp/src/include/chandler.h` (RP) and `target/atarist/src/main.s` (m68k) — never
hard-code an address inside `$FA0000`–`$FAFFFF`. Use the `APP_FREE` arena at
`$FA2300`; keep clear of the framebuffer at `$FAE0C0`. Single-producer/
single-consumer per ring, so no locks if each index is owned by one side.
