---
id: STORY-03
epic: EPIC-11
title: Reverse-DNS the connected node hostnames
status: todo
---

## Goal

Resolve each connected node's IP to a hostname (PTR / reverse DNS) when possible, so
the UI and logs can show a friendly name instead of a bare IP.

## Tasks

- [ ] On connect, start a reverse-DNS lookup for the peer IP without blocking the relay (asyncio `loop.getnameinfo` / a thread executor)
- [ ] Cache the result per IP; fall back to the IP string when resolution fails or times out
- [ ] Store the resolved host on the `Player` and include it in the status snapshot (STORY-04)
- [ ] Bound the lookup with a short timeout so a slow/missing resolver never stalls a connection or the event loop

## Acceptance

A connected node whose IP has a PTR record shows its hostname (the IP otherwise) in
`status.json` and the UI, with no measurable relay-latency impact.

## Notes

Best-effort and fully off the relay path. Most LAN/home IPs won't have a PTR record —
the IP fallback must be graceful and the common case.
