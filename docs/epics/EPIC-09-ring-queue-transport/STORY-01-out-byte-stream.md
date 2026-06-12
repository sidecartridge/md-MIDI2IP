---
id: STORY-01
epic: EPIC-09
title: OUT byte-stream — fire-and-forget Bconout over commemul (bit 8)
status: in-progress
---

## Goal

Replace the per-byte `CMD_MIDI_SEND` handshake on the **MIDI OUT** path (ST→RP) with
a fire-and-forget commemul byte stream: each `Bconout(3)` byte is a single ROM3 read,
captured by the existing PIO/DMA ring and routed straight to the network — no
TPROTOCOL frame, no token spin.

## Tasks

- [ ] Establish the commemul MIDI sample routing in `chandler_consume_rom3_sample`: branch on the high marker bits *before* the TPROTOCOL parser (`if (s & 0x200) …; else if (s & 0x100) …; else tprotocol_parse(s)`)
- [ ] RP: on a bit-8 sample (`0x100 | byte`), push `s & 0xFF` to the network OUT path (`midi_net_send_byte`)
- [ ] m68k `userfw.s` `.mbt_out`: emit one `tst.b (a0, #(0x100|byte))` ROM3 read, then chain to the original `Bconout` — drop the `send_sync`/`CMD_MIDI_SEND` call
- [ ] Define the named constants/offsets (the `0x100` OUT marker, the ROM3 base) symbolically on both sides
- [ ] Verify byte-exact, in-order OUT delivery against the orchestrator (e.g. a Hatari node sending names / master-slave)

## Acceptance

A MIDI Maze node's outgoing MIDI (including a multi-KB SEND-DATA burst) reaches the
orchestrator byte-exact and in order, with no per-byte command round-trip — OUT
throughput well above the 31250-baud wire rate.

## Notes

This is the half that carries the heavy maze burst. Model: md-devops's `0xFF00`
byte-stream consumer. Pairs with STORY-02 (IN). The TPROTOCOL command channel stays
for config/menu (time-disjoint from gameplay).
