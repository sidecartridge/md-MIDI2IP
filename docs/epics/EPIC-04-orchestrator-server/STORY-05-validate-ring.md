---
id: STORY-05
epic: EPIC-04
title: Validate — two clients form a ring and exchange bytes
status: todo
milestone: alpha-mvp
---

## Goal

Prove the server end to end: two clients connect, the ring forms, and bytes one
sends arrive at the other (and back around), with the HTTP status reflecting it.

## Tasks

- [ ] Two clients (a small stdlib test client, or two `tools/echo_peer.py`-style senders) connect and form a 2-ring
- [ ] Bytes A sends arrive at B in order, and B's arrive at A — byte-exact, no loss/reorder
- [ ] The HTTP status / JSON shows both players, their byte counters, and the ring order
- [ ] A client drop re-forms the ring; reconnect rejoins cleanly (with STORY-04)

## Acceptance

Two clients exchange bytes through the server's ring with byte-exact delivery, and
the HTTP status accurately reflects the live state.

## Notes

This validates the *transport server*, not gameplay — real MIDI Maze validation
arrives when a real player (ST+RP, or the EPIC-05 Hatari gateway) joins the ring.
A throwaway Python test client is enough here.
