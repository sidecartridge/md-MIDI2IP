---
id: STORY-04
epic: EPIC-03
title: Error handling, reconnect, link status
status: done
---

## Goal

Survive Wi-Fi drops and peer disconnects by reconnecting automatically, and
surface link status (LED / terminal) so the user knows what's happening.

## Tasks

- [x] Disconnect/error (`tcp_err`, peer-close) → DOWN; `midi_net_poll` reconnects with **exponential backoff** (500 ms → 8 s cap, reset on connect)
- [x] Surface state on the **on-board green LED** (blink while down/connecting, steady on when connected) + the terminal status screen (`MIDI link : up/connecting/down`) + serial transitions
- [x] Flush the IN queue on every link drop (`midi_net_flush_in_queue`) so stale pre-drop bytes can't be injected after a reconnect

## Acceptance

Pulling the peer offline and back online recovers the stream automatically;
status reflects each transition; no byte corruption after recovery.

## Notes

Backoff resets to the minimum on a successful connect. The IN-queue flush is the
"defined reset behaviour": each session starts clean. Pairs with STORY-05's
mid-handshake reconnect-recovery check.
