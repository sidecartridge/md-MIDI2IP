---
id: STORY-07
epic: EPIC-13
title: Validate a mixed TCP + WebSocket ring (ST + Hatari)
status: done
---

## Goal

A real mixed-transport ring plays MIDI Maze: one node on TCP and one on WebSocket,
through a single orchestrator.

## Tasks

- [x] Start the orchestrator with `--ws`; confirm both listeners bind and `status.json` reports the transport per node
- [x] Bring up the ST node on transport `ws` plus a TCP node (a second ST, or a Hatari gateway on `tcp`); both appear in the ring with their transport
- [x] Play a full MIDI Maze match across the mixed ring (election through gameplay), matching the EPIC-12 STORY-03 checklist
- [x] Repeat with the transports swapped (ST on `tcp`, the other node on `ws`)
- [x] Record any latency difference against the all-TCP ring (C-01)

## Acceptance

A mixed TCP + WebSocket ring elects master and plays a responsive match, with both
transport assignments working. Add a row to the EPIC-12 checklist that references this
run.

## Notes

Hardware verification, so it follows the EPIC-12 test-pass conventions. Depends on the
orchestrator listener (STORY-03) plus the firmware WebSocket client and toggle (STORY-05,
STORY-06). STORY-04 (gateway WebSocket) applies only when the other node is a Hatari peer
on WebSocket.
