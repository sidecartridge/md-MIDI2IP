---
id: EPIC-09
iteration: 2
title: Stream MIDI over the commemul ROM3 ring (drop the per-byte command handshake)
status: done
---

## Progress

**Done — MIDI Maze is playable multiplayer over IP on real hardware.** All five
stories complete: OUT byte-stream, IN ring (with confirm-ack), retire the old
command path, IN/OUT overrun + stale-queue policy, and on-hardware validation.
Landed in `bfe4429` (transport) + `5567c65` (stale-queue cleanup) + the STORY-03
command-path removal. The two corrections that mattered vs. the original design are
folded in below (Decision A, Open questions).

## Goal

Replace the per-byte m68k↔RP **command handshake** (D-12, measured ~970 B/s) with a
**fire-and-forget streaming transport** so MIDI throughput comfortably beats the
physical 31250-baud ring (~3125 B/s) instead of running ~3× slower. Today every
MIDI byte is a full `send_sync` command: the m68k ships a TPROTOCOL frame, then
**spins** waiting for the RP to echo a token (~1 ms/byte). Streaming the bytes
through the existing **commemul ROM3 DMA ring** (ST→RP) and a **direct
shared-memory ring** (RP→ST) — each side owning its own index, no token wait —
removes the per-byte round-trip entirely.

## Why commemul (the md-devops model)

`commemul.pio` already captures every ROM3 bus cycle into a DMA ring with hardware
wrap: the Atari "writes" a 16-bit value by *reading* a ROM3 address whose low bits
carry the data — one bus cycle = one DMA-deposited sample, no CPU servicing.

The OUT path **already rides commemul**, but it layers the synchronous TPROTOCOL
*command* on top (magic + cmd + size + token + checksum, then a per-frame token
spin), and ships exactly **one byte per frame** — that framing + handshake is the
ceiling, not commemul itself. md-devops shows the way out: it drives a whole frame
as an **uninterrupted burst of `tst.b` reads with zero sync between words** (one
handshake per *frame*), and it also runs a second **unframed byte-stream consumer**
— any sample whose high byte is `0xFF` (address `$FBFF00+c`) is a raw byte `c`,
with **no command protocol and no handshake at all**. That raw byte-stream path is
exactly what MIDI needs. (md-mv16-emulator only uses `romemul` and is *not* the
model here.)

## Design

**Commemul sample encoding** (16-bit, after the `^0x8000`). The one ROM3 stream
carries three things, routed in `chandler_consume_rom3_sample` *before* the parser:

| Op | Sample | Meaning |
| --- | --- | --- |
| MIDI OUT byte | `0x100 \| byte` (bit 8) | ST→RP outgoing MIDI byte |
| MIDI IN advance | `0x200` (bit 9) | ST→RP "head consumed, move forward" |
| TPROTOCOL command | `0xABCD …` frame | config/menu (unchanged) |

```c
if (s & 0x200)      midi_in_advance();        // bit 9: fast-path IN consume
else if (s & 0x100) midi_out_push(s & 0xFF);  // bit 8: outgoing MIDI byte
else                tprotocol_parse(s);        // else: command frame
```

The MIDI stream and TPROTOCOL commands are **time-disjoint** — commands run in the
boot/config menu, MIDI runs after the firmware launches into GEM — so the bit-8/9
markers never collide with a live command payload word (a mode flag can enforce it
if ever needed).

**ST→RP (MIDI OUT / `Bconout` device 3) — fire-and-forget byte stream**
- Each outgoing byte is a single `tst.b (a0, #(0x100|byte))` ROM3 read. **No frame,
  no checksum, no token spin** — emit, return, then chain to the original `Bconout`.
- The RP consumer (above) pushes `s & 0xFF` straight to the network OUT path
  (`midi_net_send_byte`).
- Throughput is bounded only by the m68k `tst.b` rate (µs/byte), far above MIDI
  wire speed — this half carries the SEND-DATA maze burst.

**RP→ST (MIDI IN / `Bconstat`+`Bconin` device 3) — RP-owned ring + fire-and-forget advance**
The m68k stays **stateless**: the RP owns the ring (read + write indices) and
proactively publishes the current **head byte** and **depth** into the shared
region (as `Bconstat` already reads a depth today).
- `Bconstat(3)`: read `MIDI_IN_COUNT` → byte-ready / not (unchanged, free).
- `Bconin(3)`: read the pre-published `MIDI_IN_BYTE` (the head), fire the bit-9
  advance (`tst.b (a0, #0x200)`), return the byte — **no read index, no
  `CMD_MIDI_RECV`, no token spin, no wait**.
- The RP consumer, on the bit-9 sample, does `read_idx++` and republishes the new
  head byte + depth.

**Decision (A): pure fire-and-forget — REVISED on hardware.** The premise ("the
225 MHz RP always advances before the ST can re-read") was **false**: the advance is
processed asynchronously by `chandler_loop`, so `MIDI_IN_STATUS` stayed stale (-1)
between the m68k firing the advance and the RP popping. MIDI Maze's tight `Bconin`
loop re-read the same byte ~13× (`IN_adv >> RX`) → corrupted ring. **Resolved with a
confirm-ack** (the documented fallback): the RP bumps `MIDI_IN_ACK` after each
pop+republish and `.mbt_in` blocks on it before returning, so `Bconin` can't return
until the byte is truly consumed. A few µs/byte; no m68k cursor needed. The bit-9
signal still feeds the RP's consumed count for flow control.

## Scope

- **In:** the OUT commemul byte-stream (m68k emit + RP consumer); the IN
  shared-memory ring (RP producer + m68k consumer with an Atari-RAM read index);
  retiring the old `CMD_MIDI_SEND`/`CMD_MIDI_RECV` path; coexistence with the
  TPROTOCOL command channel (config/menu still use chandler commands — the MIDI
  byte stream is a *second* consumer on the same sample stream); flow-control /
  overrun behaviour; throughput measurement.
- **Out:** the network transport (EPIC-03) and orchestrator (EPIC-04) stay as-is;
  MIDI-protocol awareness stays in the orchestrator (D-02); the deferred Iteration-1
  full-match re-validation + CI gate resume after this lands (EPIC-10).

## Constraints (must preserve)

- Bidirectional, byte-oriented, **opaque** (no MIDI parsing; order preserved — D-02).
- Driven only from the BIOS device-3 handlers (`Bconstat`/`Bconin`/`Bconout`,
  trap #13); BIOS register/stack contract (callee-saved regs); correct BIOS return
  values; `Bconout` still chains to the original handler.
- Shared-region named offsets only (≥ `$FA2300` APP_FREE); 64 KB region layout;
  8 KB m68k cartridge-code budget.
- The m68k **cannot write** the cartridge window — ST→RP data goes via ROM3 reads
  (commemul); m68k mutable state (the IN read index) lives in Atari RAM.

## Open questions / risks

- ~~RP always wins the advance race (decision A)~~ — **it did not**; fixed with the
  `MIDI_IN_ACK` confirm handshake (see Decision A above).
- ~~Atomicity/visibility of the published head byte + status~~ — handled: byte written
  before status; byte replicated 4× so it's endian-/swap-invariant.
- **Overrun, resolved in practice:** the pressing loss was OUT-side (`Bconout` burst
  overran per-byte `tcp_write`, `OUT > RX`), fixed with an OUT ring drained in the
  poll context. IN drop-on-full + a time-based stale flush cover the IN side.
- **Still open (deferred):** true network backpressure (stop reading the socket on a
  full IN ring) is not implemented — current policy is drop + stale-flush.

## Stories

- **STORY-01** OUT byte-stream (bit 8) — **done**
- **STORY-02** IN ring + bit-9 advance, with confirm-ack — **done**
- **STORY-03** retire the per-byte `CMD_MIDI_*` path — **done**
- **STORY-04** IN/OUT overrun, flow-control & stale-queue policy — **done**
- **STORY-05** on-hardware throughput + 2-node game validation — **done** (playable)

## Notes

Born from **D-12**: the Iteration-1 spike proved the whole stack but found the
per-byte command handshake is the throughput ceiling. Reference model: **md-devops**
(`commemul.c`/`commemul.pio` + the `0xFF00` byte-stream consumer in `chandler.c`;
the fire-and-forget `tst.b` burst in `sidecart_functions.s`). Related: D-12 (the
flaw + fix direction), D-02 (dumb byte pipe), C-01 (lock-step latency budget),
EPIC-01 (the BIOS hook), EPIC-02 (the shared region this builds on).
