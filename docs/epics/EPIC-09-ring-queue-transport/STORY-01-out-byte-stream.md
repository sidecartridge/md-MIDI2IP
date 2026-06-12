---
id: STORY-01
epic: EPIC-09
title: OUT byte-stream — fire-and-forget Bconout over commemul (bit 8)
status: done
---

## Goal

Replace the per-byte `CMD_MIDI_SEND` handshake on the **MIDI OUT** path (ST→RP) with
a fire-and-forget commemul byte stream: each `Bconout(3)` byte is a single ROM3 read,
captured by the existing PIO/DMA ring and routed straight to the network — no
TPROTOCOL frame, no token spin.

## Tasks

- [x] Establish the commemul MIDI sample routing in `chandler_consume_rom3_sample`: a raw consumer (`chandler_setRawConsumer` → `midi_rom3_consumer`) runs *before* the TPROTOCOL parser, branching on the marker bits
- [x] RP: on a bit-8 sample (`0x100 | byte`), push `s & 0xFF` to the network OUT path (`midi_net_send_byte`)
- [x] m68k `userfw.s` `.mbt_out`: emit one `tst.b (a1, byte)` ROM3 read at `$FB8100` — **emit-only, no chain** (chaining re-entered the BIOS mid-MIDI and bombed; the network is the only MIDI sink)
- [x] Define the named constants/offsets (the `0x100` OUT marker, the `$FB8000` ROM3 base) symbolically on both sides
- [x] Verify byte-exact, in-order OUT delivery against the orchestrator (playable 2-node MIDI Maze)

## Acceptance

A MIDI Maze node's outgoing MIDI (including a multi-KB SEND-DATA burst) reaches the
orchestrator byte-exact and in order, with no per-byte command round-trip — OUT
throughput well above the 31250-baud wire rate. **Met** — sustained hundreds of
bytes/sec, byte-exact, gameplay confirmed.

## Notes

This is the half that carries the heavy maze burst. Model: md-devops's `0xFF00`
byte-stream consumer. Pairs with STORY-02 (IN). The TPROTOCOL command channel stays
for config/menu (time-disjoint from gameplay).

**On hardware:** the marker is gated by `midiActive` so it can't collide with a live
command frame. Two issues surfaced under load and were fixed: `.mbt_out` must be
emit-only (chaining bombed), and per-byte `tcp_write` from the hot path dropped bytes
under the maze burst (`OUT > RX`) — fixed by an OUT ring drained to TCP in the poll
context (see STORY-04).
