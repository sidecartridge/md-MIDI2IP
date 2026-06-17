---
id: STORY-01
epic: EPIC-13
title: Transport-selection contract and decision (D-13)
status: todo
---

## Goal

Settle the wire-level decisions both ends implement before any code: how a node selects
its transport, how the orchestrator enables WebSocket, the RFC 6455 profile used, the
mixed-ring rule, and the explicit `wss` deferral. Record it as D-13 and extend the
orchestrator contract.

## Tasks

- [ ] Add D-13 to `DECISIONS.md`: WebSocket is an optional transport alongside TCP (D-03 stays the default); the byte stream stays opaque (D-02); plain `ws` only, `wss` deferred because the RP has no mbedTLS linked (`lwipopts.h` `LWIP_ALTCP_TLS=0`)
- [ ] Specify the selection model: a per-node transport toggle in the firmware (default `tcp`); the orchestrator enables an additional WebSocket listener via a CLI parameter (default off, so existing deployments are unchanged)
- [ ] Specify the RFC 6455 profile: a GET Upgrade handshake on a configurable path (default `/`); opaque MIDI bytes carried in binary frames; client-to-server frames masked, server-to-client frames unmasked; ping answered with pong; a close frame handled by reconnect
- [ ] Define mixed-ring semantics: TCP nodes and WebSocket nodes register into the same ring and relay to each other transparently (the relay is transport-agnostic); per-node telemetry records the transport
- [ ] Extend `ORCHESTRATOR-CONTRACT.md` with a "Transport" section (TCP default plus optional WebSocket) and note that framing is transport-level, not MIDI (D-02 preserved)
- [ ] Record the rationale: WebSocket traverses HTTP reverse proxies and standard ports where raw TCP on 5005 is blocked

## Acceptance

D-13 is in `DECISIONS.md`, and `ORCHESTRATOR-CONTRACT.md` has a Transport section that
the firmware and orchestrator stories implement against. No code in this story.

## Notes

This is the shared spec that de-risks the two implementations. Keep it small: the byte
stream and ring semantics do not change, only the carrier.
