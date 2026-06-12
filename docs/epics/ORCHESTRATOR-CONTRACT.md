# Orchestrator ring-router contract

The orchestrator is a Python `asyncio` server (D-03/D-08) built **in this repo**
under `orchestrator/` (**EPIC-04**, Python 3 stdlib only, revising the earlier
"separate repo" plan, D-04/D-10). This document is the shared *contract* between
the two sides: the wire format and the ring semantics the firmware (EPIC-03)
depends on and the server (EPIC-04) implements.

It captures decisions D-02 (raw bytes), D-03 (TCP), D-04 (ring topology),
D-08 (raw sockets, no host MIDI), and constraint C-01 (lock-step latency).

## The boundary

Each Atari + Pico-W is one **player** holding a single TCP connection to the
orchestrator. That connection is the entire interface:

```
 Atari (MIDI Maze)            Pico-W firmware (this repo)         Orchestrator (other repo)
  Bconout(3) ───────────────▶ capture ──▶ socket send ──────────▶ player N's MIDI OUT
  Bconin(3)/Bconstat(3) ◀──── serve ◀──── socket recv ◀────────── player N's MIDI IN
```

- **This repo (firmware):** turns MIDI Maze's BIOS device-3 MIDI I/O into one
  bidirectional raw byte stream over TCP. It knows nothing about the ring: "what
  I write is my MIDI OUT, what I read is my MIDI IN."
- **Orchestrator repo:** holds all players and routes byte streams between them via a ring.

## Wire format

- **TCP, `TCP_NODELAY`** (D-03). One connection per player.
- **Raw, opaque bytes** (D-02): exactly the bytes MIDI Maze writes/reads. No
  framing, length prefixes, MIDI parsing, or protocol layer on either side.
- **In-order, lossless, byte-exact**: TCP guarantees it; the orchestrator must not
  reorder, drop, dedupe, or coalesce in a way that changes byte order. A single
  lost/reordered byte desyncs the game.

## Ring semantics (orchestrator side)

The orchestrator emulates the MIDI Maze daisy-chain, where physically each
player's MIDI OUT feeds the next player's MIDI IN, closing the loop:

- Route bytes from **player N's OUT → player (N+1)'s IN**, preserving order.
- **Close the ring:** last player's OUT → first player's IN.
- This makes the protocol work untouched, because the bytes simply circulate:
  - **Master election:** a player emits `0x00`; if it travels the ring and returns
    to the sender, the ring is closed → that machine becomes MASTER.
  - **COUNT-PLAYERS:** `0x80` + a counter byte increments at each hop and returns
    to the MASTER with the total.
- **Membership is fixed for the duration of a game.** Players join/leave only
  between games; mid-game changes break COUNT-PLAYERS and the lock-step (C-01).
  The orchestrator assigns each player a ring position at game formation.

## Latency obligations (both sides)

MIDI Maze is **lock-step** (C-01): every write is followed by a synchronous
MIDI-IN readback, and frame rate is bounded by ring-speed. Therefore:

- The orchestrator must forward each byte to the next hop with **minimal added
  latency**, adding no batching delay beyond a few ms.
- Per-hop turnaround should match or beat the original physical ring
  (~hundreds of µs/hop at 31250 baud); we have headroom because the firmware
  intercepts before the ACIA (EPIC-07 STORY-01).
- The orchestrator must never stall one player's IN waiting on unrelated work.

## Responsibilities

| Concern | Firmware (this repo) | Orchestrator (other repo) |
| --- | --- | --- |
| Capture/inject MIDI bytes at the Atari | ✅ EPIC-01 | N/A |
| Raw byte stream over TCP+NODELAY | ✅ EPIC-03 | ✅ |
| Ring wiring OUT(N)→IN(N+1), close loop | N/A | ✅ |
| Master-election / COUNT-PLAYERS behaviour | passes bytes through, opaque | emerges from correct ring routing |
| Ring position assignment / membership | N/A | ✅ |
| Game-start gating, join/leave between games | N/A | ✅ |
| Low-latency forwarding | minimal coalescing (EPIC-03 STORY-02) | minimal forwarding latency |

## MVP vs later

- **Alpha MVP:** 2 players. The ring of 2 is the simplest case: each player's OUT
  goes to the other's IN. Connection-order assigns ring position; no lobby.
- **Post-MVP:** full ring of up to 16 entities (humans + drones), a lobby/room
  concept, reconnect/rejoin between games.

## Open questions (resolve with the orchestrator side)

- **Player identity / rooms:** MVP can assign ring position purely by connection
  order (no control messages, keeping the stream pure). Multi-room play later
  needs *some* out-of-band association at connect. Decide whether that's a tiny
  pre-stream handshake or external configuration, without polluting the byte
  stream (D-02).
- **Readback timing:** whether MIDI Maze's post-write readback blocks or
  polls-once-then-aborts is still open (EPIC-01 STORY-04 bring-up). If poll-once,
  the firmware must block the read locally until the network byte is ready; the
  orchestrator's turnaround budget tightens accordingly.
- **Disconnect mid-game:** a dropped player breaks the ring. Define whether the
  orchestrator ends the game or holds/heals the ring. For the alpha, "end the
  game, re-form between games" is almost certainly correct.
