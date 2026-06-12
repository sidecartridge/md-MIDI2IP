---
id: STORY-02
epic: EPIC-08
title: Master-election coordinator (one stable master, any launch order)
status: done
milestone: alpha-mvp
---

## Goal

Keep the MASTER **stable** so COUNT-PLAYERS completes. Ground truth (thesis Annex B
clone analysis): a node that *sends* `0x00` and gets it back becomes MASTER, but a
node that *receives* a `0x00` becomes **SLAVE**. A stray `0x00` from another node
**demotes the sitting master**. On hardware (D-11), both nodes keep emitting `0x00`,
each one demoting the master mid-count, so the count never finishes and yields "0 machines".
The natural election (with the ring-of-one self-echo) already picks a master; the job
here is to stop it being demoted.

## Tasks

- [x] **Rule (master-protection)**: once a master is established (it originates COUNT-PLAYERS / NAME-DIALOG / START-GAME), drop a **non-master's stray MASTER-ELECT `0x00`** from the forwarded bytes so it can't demote the master. Byte-selective in `RingState.feed`: count *values*, the master's own `0x00`, and in-game joystick `0x00` are untouched (the decoder distinguishes them). The ring stays fully intact, with no echo or restructure.
- [x] Master identity is the **COUNT-PLAYERS originator** (only the master originates it), not the ambiguous `0x00`, so `_observe` no longer locks master from MASTER-ELECT.
- [x] Membership change: a **join keeps the sitting master** (newcomer → SLAVE); only the **master leaving** (or empty ring) re-elects (`remove_player` → `_reset_round`, D-04).
- [x] Gated behind `--coordinate`: **off → pure dumb relay** (D-02/D-10 default); **on → master-protected**. Unit+live tested in `selftest.py` Phase D (drop non-master demote `0x00`; keep count values / master's own / joystick).

## Acceptance

With both machines connected, once a master starts COUNT-PLAYERS it **stays** master
(no demotion by stray `0x00`s) and the count settles to the right number, verified
in the `--inspect` trace and on hardware.

## Notes

The **first** place the orchestrator stops being byte-dumb (D-02): opt-in,
orchestrator-only (RP/gateway stay dumb), with the **minimal** intervention. It
drops exactly one kind of byte (a non-master's demotion `0x00`) and never injects
or restructures. Replaces the earlier echo attempt, which broke the ring and made
the master flood (see git history).
