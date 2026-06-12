---
id: STORY-02
epic: EPIC-09
title: IN ring — Bconin via RP-owned ring + bit-9 advance (with ack)
status: done
---

## Goal

Replace the per-byte `CMD_MIDI_RECV` handshake on the **MIDI IN** path (RP→ST) with a
stateless design: the RP owns the ring and pre-publishes the head byte + a Bconstat
status; `Bconin(3)` reads the head and fires a one-cycle bit-9 "advance" signal — no
read index on the m68k, no command.

## Tasks

- [x] RP: an IN ring (16 KB) fed by the network; proactively publish the head byte (`MIDI_IN_BUFFER`, byte replicated 4× — endian-proof) and a pre-baked Bconstat status (`MIDI_IN_STATUS`, -1/0) into the shared region on every change
- [x] RP consumer: on a bit-9 sample (`0x200`), `read_idx++` and republish the new head + status
- [x] m68k `.mbt_stat` (`Bconstat`): read the pre-baked `MIDI_IN_STATUS` → `move.l`/`rte`, no compute
- [x] m68k `.mbt_in` (`Bconin`): read `MIDI_IN_BYTE`, fire `tst.b $FB8200`, **wait for the RP advance-ack**, return the byte — drop `CMD_MIDI_RECV`
- [x] Ensure the head/status publish is ordered vs. the ST read (byte first, then status)

## Acceptance

A node receives its incoming MIDI (including a multi-KB burst relayed by the
orchestrator) byte-exact and in order, with no per-byte command — IN throughput well
above the 31250-baud wire rate. **Met** — `IN_adv == RX` once the ack was added;
gameplay confirmed.

## Notes

**Decision A (pure fire-and-forget) did NOT hold on hardware.** The premise — "the
225 MHz RP always advances before the 8 MHz `Bconin` can re-read" — was wrong: the
advance is a fire-and-forget ROM3 read processed asynchronously by `chandler_loop`,
so `MIDI_IN_STATUS` stayed stale (-1) in the window between the m68k firing the
advance and the RP popping. MIDI Maze's tight `Bconin` loop re-read the same byte
many times (`IN_adv` ≈ 13× `RX`) → corrupted ring → "too many machines" / glitches.

**Fix (the documented fallback, realised as an ack counter):** the RP bumps
`MIDI_IN_ACK` after every pop+republish, and `.mbt_in` snapshots it before firing the
advance and **blocks until it changes** before returning. This makes the
read+consume a confirmed handshake — `Bconin` cannot return until the RP has truly
consumed the byte, so the next `Bconstat`/`Bconin` always sees fresh state. Cost: a
few µs block per byte. The bit-9 advances still give the RP the consumed count.
