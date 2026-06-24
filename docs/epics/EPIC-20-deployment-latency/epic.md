---
id: EPIC-20
iteration: 10
title: Reduce deployment latency (host networking + nginx WS tuning)
status: done
---

## Goal

Cut avoidable per-hop latency in the dockerized deployment for the latency-sensitive
MIDI ring (C-01): remove Docker's NAT/userland-proxy hop and tune the nginx WebSocket
proxy to forward MIDI frames immediately.

## Scope

- In scope: a `NETWORK=host` launch option (`run.sh`) for the Linux server; nginx
  `/ws` `proxy_buffering off` + `proxy_socket_keepalive on` + `tcp_nodelay on`.
- Out of scope: anything that beats WAN RTT (the dominant factor); worker/connection
  tuning (not a bottleneck at these player counts); page-load tuning (gzip/sendfile).

## Stories

- STORY-01: Host networking + nginx WS-path tuning

## Notes

- `--network host` is Linux-only (a no-op on Docker Desktop/macOS); ports bind on the
  host, and the `ufw` rules from `deploy.sh` still apply.
- For the absolute lowest latency, connect the browser directly to `ws://host:5006`
  (skip the nginx `/ws` hop); the proxy is the single-port convenience.
