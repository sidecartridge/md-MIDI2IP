---
id: STORY-04
epic: EPIC-03
title: Error handling, reconnect, link status
status: todo
---

## Goal

Survive Wi-Fi drops and peer disconnects by reconnecting automatically, and
surface link status (LED / terminal) so the user knows what's happening.

## Tasks

- [ ] Detect disconnect/error and schedule a backoff reconnect
- [ ] Surface state via the LED blink status and/or terminal
- [ ] Ensure the IN queue doesn't corrupt across a reconnect (defined reset behaviour)

## Acceptance

Pulling the peer offline and back online recovers the stream automatically;
status reflects each transition; no byte corruption after recovery.

## Notes

Reuse `blink.c` Morse status conventions for link state where it fits.
