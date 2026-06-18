# Iterations

Epics are grouped into **iterations**: a time-boxed pass with a single overarching
goal. Each epic carries an `iteration: N` field in its frontmatter; the cockpit
([`STATUS.md`](STATUS.md)) groups epics under their iteration. This file is the
narrative: the goal, scope, and **outcome** of each iteration.

| Iteration | Theme | Status |
| --- | --- | --- |
| 1 | Architecture spike: build the full stack end to end | done |
| 2 | Transport redesign, HW re-validation + orchestrator revamp | done |
| 3 | Hardware test pass: ST + Hatari verification checklist | in progress |
| 4 | Optional WebSocket transport (TCP or WebSocket) | done |
| 5 | Private rooms (room-key MIDI rings) | done |

---

## Iteration 1: Architecture spike

**Goal:** stand up the entire MIDI-to-IP path end to end: BIOS device-3 hooking
(EPIC-01), the shared-region transport (EPIC-02), the network endpoint (EPIC-03),
the orchestrator (EPIC-04), the Hatari software peer (EPIC-05), config/UI
(EPIC-06), hardware validation (EPIC-07), and match coordination (EPIC-08).
Find out whether the architecture can actually carry a MIDI Maze match.

**Outcome:** the stack works end to end: bytes flow byte-exact ST↔RP↔network↔
orchestrator, master election/COUNT-PLAYERS round-trips, the Hatari gateway joins
as a real player, and the orchestrator's protocol-aware coordination layer
(`RingState` + `--coordinate`) is built and self-tested. **The spike found a
fundamental flaw: [D-12](DECISIONS.md), the per-byte m68k↔RP command handshake
caps throughput at ~970 bytes/s, ~3× slower than the original 31250-baud MIDI
ring, and it can't be tuned away** (making `chandler_loop` eager didn't move it).
That is the decisive result of the iteration: the *architecture* is proven; the
*transport* needs replacing.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-01 · MIDI call hooking | done | BIOS device-3 hook; the hook now *is* the MIDI device |
| EPIC-02 · Shared-region transport | done | 64 KB cartridge window, symbolic offsets |
| EPIC-03 · Network endpoint | done | lwIP TCP client, `TCP_NODELAY`, reconnect |
| EPIC-04 · Orchestrator server | done | asyncio ring relay + `--inspect` / `--no-http` |
| EPIC-05 · Hatari gateway | done | software peer + full match work end to end (D-09 closed) |
| EPIC-06 · Config, UI & template cleanup | done | boot menu, endpoint config, status screen |
| EPIC-07 · Hardware validation | done | measured the stack → found D-12 (CI gate moved to EPIC-10) |
| EPIC-08 · Match coordination | done | coordinator + single-node Hatari validation done (HW match → EPIC-10) |

**Carried to Iteration 2 (now EPIC-10 · Hardware validation II):** the two
validation stories that can only run after the transport fix. These are: a full
2-player match on the **RP-hardware** path (was EPIC-08 STORY-04) and the automated
CI gate (was EPIC-07 STORY-02). Both wait on D-12. The pieces that don't hit D-12
are already validated in Iteration 1: the Hatari-gateway match (EPIC-05 STORY-04)
and the smart orchestrator single-node against a real client (EPIC-08 STORY-04).

---

## Iteration 2: Transport redesign + orchestrator revamp

**Goal:** kill the per-byte handshake (D-12) so throughput beats the physical MIDI
ring and validate a full match for real, then revamp the orchestrator into a dumb
relay with real observability now that the firmware owns the ring.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-09 · Stream MIDI over the commemul ROM3 ring | done | D-12 fixed: MIDI Maze playable over IP on hardware |
| EPIC-10 · Hardware validation II | done | 2-player HW match validated by playable gameplay; build CI gate green |
| EPIC-11 · Orchestrator revamp: dumb relay + observability | done | RingState retired (`--inspect` kept); per-node `status.json` telemetry + SVG ring-viz HTML; reverse-DNS; reconnection node recycling |

**Outcome:** EPIC-09 landed: the per-byte handshake is gone (the commemul fast path:
bit-8 OUT, bit-9 IN + confirm-ack, OUT ring, stale-queue flush), and MIDI Maze plays
multiplayer over IP on real hardware (closing D-12). EPIC-10's 2-player hardware match
is validated by playable gameplay. EPIC-11 returned the orchestrator to a dumb relay
with real observability: a live SVG ring view polling per-node telemetry, reverse-DNS
names, reconnection node recycling, and an end-user README usage guide. **Iteration
complete.**

---

## Iteration 3: Hardware test pass

**Goal:** turn the ad-hoc hardware validation from Iterations 1 and 2 into a standing,
repeatable test checklist for each release, run on a physical Atari ST (Booster-installed
firmware) and a Hatari node against one orchestrator. Cover the paths that were never
exercised end to end: multi-node rings past two players, and the disconnect/reconnect
recovery cases.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-12 · Hardware test pass (ST + Hatari) | todo | manual checklist: boot/config, ring join, full match, multi-node + recovery |

**Outcome:** pending.

---

## Iteration 4: Optional WebSocket transport

**Goal:** let a node reach the orchestrator over WebSocket instead of the raw TCP
socket, chosen per node and enabled per orchestrator, without disturbing the default
TCP path. Raw TCP on port 5005 is often blocked or unroutable through HTTP reverse
proxies and cloud frontends; WebSocket rides a standard HTTP port and an Upgrade
handshake. The MIDI byte stream stays opaque (D-02); WebSocket only wraps the carrier.
TCP stays the default, and a TCP node and a WebSocket node can share one ring.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-13 · Optional WebSocket transport | done | stdlib RFC 6455 on the orchestrator (mixed ring), a firmware WebSocket client + toggle, gateway parity; `wss` deferred |

**Outcome:** EPIC-13 landed: WebSocket is an opt-in carrier alongside the default TCP,
selectable per node and enabled per orchestrator, with TCP and WebSocket nodes sharing
one ring. The orchestrator hand-rolls RFC 6455 on the standard library (handshake plus a
streaming frame codec) and serves both listeners on separate ports through a
transport-agnostic relay. The firmware carries the same opaque byte stream (D-02) over
masked binary frames, with a `[T]ransport` boot-menu toggle and a port per carrier. Both
transports play MIDI Maze on real hardware. One regression surfaced and was fixed: a
disconnect-removal change that dropped a peer on a transient relay write error collapsed
a 2-node ring into a self-echo flood, which slowed both carriers until it was reverted to
the tolerant relay. `wss` / TLS stays deferred (the RP has no mbedTLS linked).

---

## Iteration 5: Private rooms

**Goal:** split the single global ring into multiple private rings keyed by a human-typed
room key, so groups of players get their own isolated MIDI Maze ring. A WebSocket node
carries its room key in the handshake (`Authorization: Bearer`), the orchestrator routes it
to that room's ring, and rooms are pre-provisioned by an operator through a small REST API
(admin-key for writes) so an unknown key is refused. The web view gains a room selector. A
plain-TCP node joins a default room, and the key gates a ring rather than securing traffic
(no TLS; put it behind a reverse proxy if exposed).

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-14 · Private rooms | done | per-room rings + REST provisioning (admin-key), `Authorization: Bearer` room key on WS, room lifecycle (16-cap, auto-codes, TTL) + persistence, per-room phase/master + lobby page, firmware `[R]oom` menu + gateway `--room` |

**Outcome:** EPIC-14 landed: one orchestrator now hosts many private rings keyed by a
human-typed room key. A WebSocket node carries its key as `Authorization: Bearer`; the
orchestrator routes it to that room's ring, with a plain-TCP node on the default ring.
Rooms are pre-provisioned over a small REST API (admin-key for writes, unknown keys
refused), each ring caps at 16 players, empty rooms are reaped on a TTL, and the
provisioned set persists across restarts. The web view scopes to one room with a selector,
a lobby lists every room with its player count and game phase, and the master node is
badged from the read-only inspector. The Hatari gateway joins with `--room` and the
firmware with a `[R]oom` boot-menu entry. Validated on real hardware (two isolated rooms,
ST + Hatari). Two browser/bench bugs were found and fixed along the way: the room dropdown
built SVG-namespaced options, and the menu Server line froze after a config-edit reconnect.
**Iteration complete.**
