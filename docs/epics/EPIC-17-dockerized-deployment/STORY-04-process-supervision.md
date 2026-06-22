---
id: STORY-04
epic: EPIC-17
title: Single-image process supervision + ports + logging
status: in-progress
---

## Goal

One image runs nginx + orchestrator together reliably, with clean logs and
shutdown.

## Tasks

- [x] Add supervisord (or s6-overlay) to run nginx and `orchestrator.py` as managed
      processes (restart on crash).
- [x] `EXPOSE 80 5005 5006 8080`; document the published ports.
- [x] Aggregate both services' logs to the container stdout/stderr.
- [ ] Handle SIGTERM so `docker stop` shuts both down cleanly.
- [x] Optional: a `HEALTHCHECK` hitting the HTTP status port.

## Acceptance

`docker run` starts both services; killing either lets the supervisor restart it;
`docker stop` exits cleanly; both services' logs are visible via `docker logs`.

## Notes

Keep the supervisor minimal — two long-running children, logs to stdout.
