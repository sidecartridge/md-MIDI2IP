---
id: STORY-04
epic: EPIC-04
title: Robustness: half-open detection, buffers, shutdown
status: done
---

## Goal

Keep the server stable across the messy realities of player connections: ungraceful
drops, slow/half-open links, and clean shutdown.

## Tasks

- [x] TCP keepalive on every player socket (`_enable_keepalive`, same as `tools/echo_peer.py`); a silently-dead player surfaces and is deregistered
- [x] Bounded write buffer (`set_write_buffer_limits`) + a `drain` timeout: a stuck player is **dropped** (`_drop_player`) so it can't freeze the lock-step ring or grow memory
- [x] Clean shutdown via `loop.add_signal_handler` (SIGINT/SIGTERM): stop, close all player sockets, exit without a traceback (KeyboardInterrupt fallback for Windows)
- [x] Defensive: `ConnectionError`/`OSError` logged at info, a broad `except Exception` keeps one bad connection from taking down the server (asyncio also isolates each handler)
- [x] **One connection per private IP**: a new connection supersedes any existing connection from the same **private-network** IP (a LAN node = one IP); a reconnect drops the node's stale half-open connection instead of a phantom 2nd player. **Public** IPs (a NAT gateway may legitimately hide many players) and **loopback** (local testing) are exempt (`ipaddress`-based classification).

## Acceptance

Killing a player ungracefully removes it and re-forms the ring within seconds; a
slow player doesn't exhaust memory or freeze others; Ctrl-C exits cleanly.

## Notes

Mirrors the hardening already in `tools/echo_peer.py` (keepalive, supersede stale,
catch errors), scaled to N concurrent players. Decide the policy when a slow
player can't keep up (drop bytes vs disconnect it) and log it; don't silently
stall the ring.
