# Orchestrator ring-router contract

The orchestrator is a Python `asyncio` server (D-03/D-08) built **in this repo**
under `orchestrator/` (**EPIC-04**, Python 3 stdlib only, revising the earlier
"separate repo" plan, D-04/D-10). This document is the shared *contract* between
the two sides: the wire format and the ring semantics the firmware (EPIC-03)
depends on and the server (EPIC-04) implements.

It captures decisions D-02 (raw bytes), D-03 (TCP), D-04 (ring topology),
D-08 (raw sockets, no host MIDI), D-13 (optional WebSocket transport), and
constraint C-01 (lock-step latency).

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

## Transport (TCP default, optional WebSocket)

The carrier under the byte stream is selectable (D-13). The stream itself does not
change: the same opaque, in-order, byte-exact bytes (D-02), whichever transport carries
them.

- **TCP (default).** Raw TCP with `TCP_NODELAY` (D-03), one connection per player. This
  is the original path and stays the default on both ends.
- **WebSocket (optional).** RFC 6455 over the same TCP connection, chosen per node and
  enabled per orchestrator. A node carries its MIDI bytes in WebSocket binary frames,
  and the orchestrator runs an extra WebSocket listener next to the TCP one. It exists so
  a node can reach an orchestrator behind an HTTP reverse proxy or on a standard port,
  where raw TCP on 5005 is blocked.

Selection:

- **Node (firmware or gateway):** a persisted transport setting, default `tcp`. The
  node stores a port per carrier (a TCP port and a WebSocket port), because the
  orchestrator's two listeners bind different ports; the toggle selects the carrier and
  its matching port together.
- **Orchestrator:** a CLI parameter enables the WebSocket listener (default off, so an
  existing deployment is unchanged). The TCP and WebSocket listeners run at the same time
  on different ports (`--port` 5005, `--ws-port` 5006 by default).

WebSocket profile:

- The client opens with a GET Upgrade handshake on a configurable path (default `/`); the
  server replies `101` with the computed `Sec-WebSocket-Accept`.
- MIDI bytes ride in **binary** frames. Framing is transport-level only, not MIDI parsing
  (D-02 holds): a frame payload is an opaque run of the same bytes.
- Client-to-server frames are masked (required by RFC 6455); server-to-client frames are
  unmasked. A `ping` is answered with a `pong`; a `close` is handled by reconnect.

Mixed ring: a TCP node and a WebSocket node register into the same ring and relay to each
other. The relay is transport-agnostic, so ring order and the MIDI Maze protocol (master
election, COUNT-PLAYERS) behave the same regardless of each node's carrier. Per-node
telemetry records the transport.

Not in scope: `wss` / TLS. The RP firmware has no mbedTLS linked (`lwipopts.h`
`LWIP_ALTCP_TLS=0`), so a secure socket is a separate effort. Terminate TLS at a reverse
proxy and speak `ws` to the orchestrator on the internal network.

## Rooms (private rings)

A room key splits the single ring into many private rings (D-14). Players that present the
same key share one ring, isolated from other rooms. Rooms ride the WebSocket carrier; a
plain-TCP node joins a single default room.

Room key:

- Human-typed and case-insensitive, normalized to uppercase. Characters `A-Z 0-9`, 1 to 16
  long (fits the firmware config and is easy to type). An empty key means the default room.
- Carried on the WebSocket handshake as `Authorization: Bearer <roomkey>` (D-13), or, for
  a browser (which cannot set request headers on a WebSocket), as a `?room=<roomkey>` query
  parameter on the handshake path; the header wins when both are present. A TCP node has no
  handshake, so it always joins the default room.

Provisioning (REST, on the HTTP status port):

- `GET /rooms` (open): list rooms with a per-room summary (player count, cap, phase).
- `POST /rooms` (admin): create a room. With a key it creates that named room; with no key
  it returns a short auto-generated code (uppercase, ambiguous characters removed).
- `DELETE /rooms/{key}` (admin): delete a room and close its players.
- Admin writes require an `X-Admin-Key` header matching `--admin-key`, and are refused when
  `--admin-key` is unset. Reads are open.
- A WS join whose key is not provisioned is refused at the handshake (HTTP 403). The
  default room is always present and needs no provisioning.

Routing:

- One ring per room. The relay forwards OUT(N) to IN(N+1) within a room only (D-04); a room
  of one echoes to itself. A connection is identified by its full remote endpoint
  (`ip:port`), so many players can share one IP; a half-open connection from an ungraceful
  drop is reaped by TCP keepalive. Telemetry is room-scoped.

Lifecycle:

- A room caps at 16 players (D-04, the MIDI Maze ring limit); an over-cap join is refused.
- An empty non-default room is reaped after a TTL; the default room is never reaped.
- The provisioned room set persists to a JSON file and reloads on restart. Player state is
  not persisted; players reconnect into the room.

Status and UI:

- `GET /status.json?room=KEY` returns one room's snapshot in the per-node schema above; no
  param means the default room.
- The ring view has a room selector (from `/rooms`) and badges each room's phase and master
  node. A lobby page lists all rooms with their counts and phase.
- Phase and master come from the read-only `--inspect` decoder run per room, off the relay
  path, so D-02 holds.

Security: the room key gates a ring, it does not secure the traffic. Without TLS (`wss`
deferred, D-13) the key and the MIDI bytes travel in clear text. Terminate TLS and guard
the admin routes at a reverse proxy for an exposed deployment.

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
