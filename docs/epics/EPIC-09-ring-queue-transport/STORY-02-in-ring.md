---
id: STORY-02
epic: EPIC-09
title: IN ring — fire-and-forget Bconin via RP-owned ring + bit-9 advance
status: in-progress
---

## Goal

Replace the per-byte `CMD_MIDI_RECV` handshake on the **MIDI IN** path (RP→ST) with a
stateless fire-and-forget design: the RP owns the ring and pre-publishes the head
byte + depth; `Bconin(3)` reads the head and fires a one-cycle bit-9 "advance"
signal — no read index on the m68k, no command, no wait.

## Tasks

- [ ] RP: an IN ring (`MIDI_IN_RING` + read/write indices) fed by the network; proactively publish the head byte (`MIDI_IN_BYTE`) and depth (`MIDI_IN_COUNT`) into the shared region on every change
- [ ] RP consumer: on a bit-9 sample (`0x200`), `read_idx++` and republish the new head + depth
- [ ] m68k `.mbt_stat` (`Bconstat`): read `MIDI_IN_COUNT` → byte-ready (unchanged, free)
- [ ] m68k `.mbt_in` (`Bconin`): read `MIDI_IN_BYTE`, fire `tst.b (a0, #0x200)`, return the byte — drop the `send_sync`/`CMD_MIDI_RECV` call
- [ ] Ensure the head/depth publish is ordered vs. the ST read (write the byte before bumping the depth)

## Acceptance

A node receives its incoming MIDI (including a multi-KB burst relayed by the
orchestrator) byte-exact and in order, with no per-byte command — IN throughput well
above the 31250-baud wire rate.

## Notes

Decision A (pure fire-and-forget): the 225 MHz RP poll always advances the head
before the 8 MHz `Bconin` loop can re-read, so no duplicate and no m68k cursor. The
bit-9 advances also give the RP the consumed count for backpressure (STORY-04).
