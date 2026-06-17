---
id: STORY-04
epic: EPIC-12
title: Multi-node scaling and recovery paths
status: todo
---

## Goal

The ring holds up past two players and recovers from the disconnect and reconnect cases
a real session hits.

## Tasks

- [ ] Add a third node (any mix of ST + SidecarTridge and Hatari + gateway); all three appear on the ring and a 3-player match plays
- [ ] Reconnection node recycling: drop a node's link and reconnect from the same IP; the stalled prior entry is superseded and the reconnection takes a fresh node id
- [ ] Restart the orchestrator while nodes are up; nodes reconnect and re-form the ring without a manual reset
- [ ] Drop Wi-Fi on the ST node and restore it; the node reconnects to the orchestrator and rejoins the ring
- [ ] Stall one node (pause its Hatari); the slow-player drop plus the stale-queue flush keep the other nodes from freezing
- [ ] Record the largest player count actually exercised (target up to 16) and note any node that misbehaves

## Acceptance

A ring of three or more plays, same-IP reconnects recycle the node id, and the ring
survives an orchestrator restart, a Wi-Fi drop, and a stalled node. Write the maximum
node count reached here.

## Notes

Reconnection node recycling and the slow-player drop / stale-queue flush come from
EPIC-11 and EPIC-09 (`MIDI_QUEUE_STALE_MS`, `RECONNECT_STALE_S`). Up to 16 players is the
MIDI Maze ceiling.
