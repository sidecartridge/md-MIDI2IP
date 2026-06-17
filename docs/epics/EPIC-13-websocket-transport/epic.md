---
id: EPIC-13
iteration: 4
title: Optional WebSocket transport (TCP or WebSocket)
status: todo
---

## Goal

Add WebSocket as an alternative to the raw TCP socket for the node-to-orchestrator
link, selectable per node and enabled per orchestrator, without removing or changing
the default TCP path. Raw TCP on a custom port (5005) is often blocked by firewalls and
cannot pass through an HTTP reverse proxy or many cloud frontends. WebSocket rides a
standard HTTP port and an Upgrade handshake, so a node can reach an orchestrator hosted
behind nginx, Cloudflare, or a PaaS load balancer. The MIDI byte stream stays opaque
(D-02); WebSocket is only a transport wrapper around the same bytes.

## Scope

- In scope: a stdlib RFC 6455 WebSocket layer on the orchestrator (an additional
  listener that shares the ring with TCP nodes); a WebSocket client in the
  microfirmware over the existing lwIP TCP PCB; a persisted transport toggle plus boot
  menu in the firmware; a CLI parameter to enable WebSocket on the orchestrator;
  optional WebSocket parity in the Hatari gateway; the wire decision (new D-13) and a
  contract update.
- Out of scope: `wss` / TLS. The RP has no mbedTLS linked (`lwipopts.h`:
  `LWIP_ALTCP_TLS=0`), so a secure socket is a separate, larger epic; operators who need
  TLS terminate it at a reverse proxy and speak `ws` to the orchestrator on the internal
  network. Also out: removing or changing the TCP path (it stays the default), and any
  MIDI parsing (D-02 holds, framing is transport-level only).

## Stories

- STORY-01: Transport-selection contract and decision (D-13)
- STORY-02: Orchestrator stdlib WebSocket handshake and frame codec
- STORY-03: Orchestrator WebSocket listener and transport-agnostic relay (mixed ring)
- STORY-04: Hatari gateway WebSocket client (validates the WS path before the firmware)
- STORY-05: Microfirmware WebSocket client transport
- STORY-06: Microfirmware transport toggle (config + boot menu)
- STORY-07: Validate a mixed TCP + WebSocket ring (ST + Hatari)

## Notes

WebSocket framing is a transport wrapper around the opaque byte stream; it does not
parse MIDI (D-02) and does not change the ring semantics (D-04, the orchestrator still
routes OUT(N) to IN(N+1)). The relay stays single-path: TCP and WebSocket connections
register into the same `Registry` and relay to each other. References: D-02 (opaque byte
pipe), D-03 (TCP default), D-04 (ring topology), C-01 (lock-step latency), and the
analysis anchors `rp/src/midi.c:159-275`, `orchestrator/orchestrator.py:261-357,478-586`,
`hatari-gateway/gateway.py:95-172`. Hardware verification rides the EPIC-12 checklist.
