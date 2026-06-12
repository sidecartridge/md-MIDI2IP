# Iterations

Epics are grouped into **iterations** — a time-boxed pass with a single overarching
goal. Each epic carries an `iteration: N` field in its frontmatter; the cockpit
([`STATUS.md`](STATUS.md)) groups epics under their iteration. This file is the
narrative: the goal, scope, and **outcome** of each iteration.

| Iteration | Theme | Status |
| --- | --- | --- |
| 1 | Architecture spike — build the full stack end to end | done |
| 2 | Transport redesign + hardware re-validation | in progress (EPIC-09 done, EPIC-10 todo) |
| 3 | Orchestrator revamp — dumb relay + observability | todo (EPIC-11) |

---

## Iteration 1 — Architecture spike

**Goal:** stand up the entire MIDI-to-IP path end to end — BIOS device-3 hooking
(EPIC-01), the shared-region transport (EPIC-02), the network endpoint (EPIC-03),
the orchestrator (EPIC-04), the Hatari software peer (EPIC-05), config/UI
(EPIC-06), hardware validation (EPIC-07), and match coordination (EPIC-08) —
and find out whether the architecture can actually carry a MIDI Maze match.

**Outcome:** the stack works end to end — bytes flow byte-exact ST↔RP↔network↔
orchestrator, master election/COUNT-PLAYERS round-trips, the Hatari gateway joins
as a real player, and the orchestrator's protocol-aware coordination layer
(`RingState` + `--coordinate`) is built and self-tested. **But the spike found a
fundamental flaw: [D-12](DECISIONS.md) — the per-byte m68k↔RP command handshake
caps throughput at ~970 bytes/s, ~3× slower than the original 31250-baud MIDI
ring, and it can't be tuned away** (making `chandler_loop` eager didn't move it).
That is the decisive result of the iteration: the *architecture* is proven, the
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
validation stories that can only run after the transport fix — a full 2-player
match on the **RP-hardware** path (was EPIC-08 STORY-04) and the automated CI gate
(was EPIC-07 STORY-02). Both wait on D-12. The pieces that *don't* hit D-12 are
already validated in Iteration 1: the Hatari-gateway match (EPIC-05 STORY-04) and
the smart orchestrator single-node against a real client (EPIC-08 STORY-04).

---

## Iteration 2 — Transport redesign

**Goal:** kill the per-byte handshake (D-12) so throughput beats the physical MIDI
ring, then validate a full match for real.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-09 · Stream MIDI over the commemul ROM3 ring | done | D-12 fixed — MIDI Maze playable over IP on hardware |
| EPIC-10 · Hardware validation II | todo | full 2-player HW match + CI gate; gated on EPIC-09 |

**Outcome (in progress):** EPIC-09 landed — the per-byte handshake is gone (the
commemul fast path: bit-8 OUT, bit-9 IN + confirm-ack, OUT ring, stale-queue flush),
and MIDI Maze plays multiplayer over IP on real hardware (closing D-12). EPIC-10
(full 2-player HW match + CI gate) remains.

EPIC-10 carries the two Iteration-1 validation stories that were blocked by D-12:
STORY-01 (automated CI gate, from EPIC-07) and STORY-02 (full 2-player hardware
match, from EPIC-08).

---

## Iteration 3 — Orchestrator revamp

**Goal:** with the firmware now owning the MIDI ring (EPIC-09), simplify the
orchestrator back to a dumb byte relay and give it real observability — a live ring
visualization, per-node telemetry, reverse-DNS naming, and stale-buffer hygiene.

**Epics**

| Epic | Status | Note |
| --- | --- | --- |
| EPIC-11 · Orchestrator revamp — dumb relay + observability | todo | retire RingState (keep `--inspect`); status.json telemetry + ring-viz HTML; reverse-DNS; 10 s stale-buffer cleanup |
