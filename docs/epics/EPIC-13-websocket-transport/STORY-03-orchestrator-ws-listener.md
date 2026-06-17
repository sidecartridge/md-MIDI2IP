---
id: STORY-03
epic: EPIC-13
title: Orchestrator WebSocket listener and transport-agnostic relay (mixed ring)
status: done
---

## Goal

A WebSocket node joins the orchestrator's ring and relays byte-exact with TCP nodes,
while the relay loop stays single-path.

## Tasks

- [x] Introduce a small connection abstraction (`read(n)` / `write(bytes)` / `drain()` / `close()` plus peer and socket info) with a raw-TCP backend wrapping the existing `StreamReader`/`StreamWriter` and a WebSocket backend wrapping the STORY-02 codec
- [x] Refactor `handle_player` and the `Player` record (`orchestrator.py:166-179,261-357`) onto that abstraction so the ring relay loop (`orchestrator.py:316-342`) is identical for both transports
- [x] Add the WebSocket listener: a second `asyncio.start_server` that runs the handshake, then registers the upgraded connection as a `Player` in the same `Registry` (one mixed ring)
- [x] Add the CLI parameter: `--ws` to enable the listener and `--ws-port` (default 5006) for its port; with `--ws` absent the orchestrator behaves exactly as today (`orchestrator.py:566-586`)
- [x] Apply the existing socket tuning to WebSocket connections: `TCP_NODELAY` on the underlying socket, keepalive, the write-buffer limit, and the slow-player drain timeout
- [x] Add `transport` (`tcp` / `ws`) to the per-node `status.json` telemetry and surface it in the ring view
- [x] Selftest phase: a WebSocket client and a TCP client form one ring and exchange bytes byte-exact

## Acceptance

With `--ws`, a WebSocket client and a TCP client sit in the same ring and relay
byte-exact; without `--ws` the orchestrator is unchanged; `status.json` reports each
node's transport. Selftest green.

## Notes

The relay stays transport-agnostic, so the EPIC-11 features (dedup, reconnection node
recycling, telemetry) keep working for both backends. Builds on STORY-02.
