---
id: STORY-03
epic: EPIC-05
title: Orchestrator client (connect, reconnect, status)
status: done
milestone: alpha-mvp
---

## Goal

Make the gateway a well-behaved orchestrator client: connect to a configured
`host:port`, survive drops, and report what it's doing. Mirrors the RP's
`midi_net_*` behaviour (EPIC-03 STORY-01/04).

## Tasks

- [x] Connect to a configurable orchestrator host:port (CLI arg / env), `TCP_NODELAY`
- [x] Reconnect with backoff on drop/error; resume bridging once reconnected
- [x] On a drop, discard stale in-flight bytes so a reconnect starts clean (the gateway's analogue of the RP IN-queue flush)
- [x] Log link state transitions (down / connecting / up) to stdout

## Acceptance

The gateway connects to the orchestrator and bridges; killing/restarting the
orchestrator (or a network blip) auto-reconnects and resumes, with clear status
logging.

## Notes

This is the EPIC-03 STORY-01/04 logic re-expressed in Python: same state machine
(down/connecting/up), backoff, and clean-on-reconnect. Keep it stdlib (`socket` /
`asyncio`). No HTTP status here; that is the orchestrator's job (EPIC-04 STORY-03).
