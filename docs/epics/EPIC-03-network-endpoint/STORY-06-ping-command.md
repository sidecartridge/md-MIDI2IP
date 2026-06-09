---
id: STORY-06
epic: EPIC-03
title: Endpoint liveness ping command
status: todo
---

## Goal

Give the user (and the harness) a way to confirm the remote MIDI endpoint is
alive without sending MIDI traffic.

## Tasks

- [ ] `ping` command: probe the configured endpoint and report reachable/unreachable + round-trip time
- [ ] Make the ping non-blocking (poll-mode lwIP) so it never stalls the bus loop
- [ ] Surface the result over the serial debug console (machine-readable) and the terminal UI
- [ ] Bounded timeout so a dead peer reports unreachable promptly

## Acceptance

`ping` against a reachable peer reports success + RTT; against a dead peer it
reports unreachable within the bounded timeout, without stalling the bus loop.

## Notes

Choose a probe that suits the transport from EPIC-03 STORY-01 (e.g. TCP connect
check, or an app-level ping if a framed protocol is used). The `status` command
lives in EPIC-04 STORY-02; this story only adds liveness probing.
