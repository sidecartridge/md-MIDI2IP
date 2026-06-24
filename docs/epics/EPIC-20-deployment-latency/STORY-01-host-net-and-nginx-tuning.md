---
id: STORY-01
epic: EPIC-20
title: Host networking + nginx WS-path tuning
status: done
---

## Goal

Lower per-hop latency: an optional host-network launch mode plus immediate WS frame
forwarding through nginx.

## Tasks

- [x] `run.sh`: `NETWORK=host` option (`--network host`, omit `-p`); documented in
      `.env.example`.
- [x] nginx `/ws`: `proxy_buffering off` + `proxy_socket_keepalive on`; `tcp_nodelay
      on` at the server.
- [x] Build + validate: nginx config valid and the WS handshake still upgrades (101).
- [x] Confirm on the Linux server with `NETWORK=host` (host mode is a no-op on macOS).

## Acceptance

The image builds, `nginx -t` is valid, `/ws` still upgrades (101), and `NETWORK=host`
runs on the Linux server with the ports bound directly on the host.

## Notes

Gains are modest versus WAN RTT; the biggest win is removing the Docker NAT hop on the
server. Direct `ws://host:5006` (no nginx) remains the lowest-latency client path.
