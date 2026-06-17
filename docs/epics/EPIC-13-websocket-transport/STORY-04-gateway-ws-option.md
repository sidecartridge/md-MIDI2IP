---
id: STORY-04
epic: EPIC-13
title: Hatari gateway WebSocket client (validates the WS path)
status: done
---

## Goal

Give the Hatari gateway a WebSocket client so a known-good, easy-to-debug node exercises
the orchestrator's WebSocket path end to end before the firmware client. A Hatari node
can then speak WebSocket where only the WebSocket listener is reachable, and the gateway
proves STORY-02 and STORY-03 against a real client.

## Tasks

- [x] Add `--transport tcp|ws` (default `tcp`) to `gateway.py` (`hatari-gateway/gateway.py:143-154`)
- [x] When `ws`, after `socket.create_connection` (`gateway.py:169`) perform the client handshake (random key, validate the 101 and accept value) before `bridge()`
- [x] Wrap the socket so `bridge()` (`gateway.py:95-131`) sends masked binary frames and decodes incoming frames with no other change; answer a server ping with a pong
- [x] Share the WebSocket helper with the orchestrator codec (a small stdlib-only module both import) rather than duplicating it
- [x] Add selftest coverage for the gateway WebSocket framing path

## Acceptance

A Hatari node with `--transport ws` joins a WebSocket-enabled orchestrator and relays
byte-exact; the default `tcp` behavior is unchanged. Selftest green.

## Notes

Sequenced before the firmware WebSocket client (STORY-05) on purpose: the gateway is
Python and quick to iterate, so it confirms the orchestrator WebSocket path works before
the riskier firmware implementation. The parity value remains, since a Hatari node can
use WebSocket in production; the orchestrator running both listeners (STORY-03) also lets
a gateway stay on TCP.
