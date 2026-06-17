---
id: STORY-02
epic: EPIC-12
title: Ring join and orchestrator observability
status: todo
---

## Goal

Each node registers with the orchestrator and is visible in the live ring view with
correct per-node telemetry.

## Tasks

- [ ] The ST node connects and appears on the ring view at `http://<orchestrator-ip>:8080/`, which refreshes every 2 s
- [ ] The Hatari node connects and appears as a second node on the same ring
- [ ] Each node shows its IP and reverse-DNS host (or the IP when no PTR record resolves)
- [ ] `status.json` reports per node in ring order: `id`, `ip`, `host`, `peer`, `connected_s`, `idle_s`, `bytes_out`, `bytes_in`; the byte counters climb as MIDI flows
- [ ] Running the orchestrator with `--inspect` logs decoded MIDI Maze events off the relay path; `--no-http` disables the status page

## Acceptance

Both nodes appear on the ring view in ring order with their host or IP, and `status.json`
telemetry tracks live traffic. Capture a screenshot of the ring view and a `status.json`
sample here.

## Notes

Telemetry shape and the SVG ring view come from EPIC-11. Reverse-DNS falls back to the IP
on timeout or no record (`DNS_TIMEOUT_S`).
