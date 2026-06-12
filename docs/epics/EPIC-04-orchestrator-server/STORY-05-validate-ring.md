---
id: STORY-05
epic: EPIC-04
title: Validate: two clients form a ring and exchange bytes
status: done
milestone: alpha-mvp
---

## Goal

Prove the server end to end: two clients connect, the ring forms, and bytes one
sends arrive at the other (and back around), with the HTTP status reflecting it.

## Tasks

- [x] `orchestrator/selftest.py` spawns the server + two stdlib clients forming a 2-ring (one command, exit 0 = PASS)
- [x] A→B and B→A byte-exact (`recv_exact`), no loss/reorder
- [x] `/status.json` shows 2 players online, ring length 2, per-player byte counters
- [x] A client drop re-forms the ring (1 online); a reconnect rejoins (2 online) and relays again
- [x] One-connection-per-private-IP classification (STORY-04): private LAN IPs dedup; public (NAT) and loopback are exempt

## Acceptance

Two clients exchange bytes through the server's ring with byte-exact delivery, and
the HTTP status accurately reflects the live state.

## Notes

This validates the *transport server*, not gameplay. Real MIDI Maze validation
arrives when a real player (ST+RP, or the EPIC-05 Hatari gateway) joins the ring.
A throwaway Python test client is enough here.
