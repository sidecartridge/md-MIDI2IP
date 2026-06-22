---
id: STORY-02
epic: EPIC-17
title: Orchestrator service layer + parameter passing
status: done
---

## Goal

The image runs `orchestrator.py` with all listeners on 0.0.0.0, configured from
`docker run` parameters.

## Tasks

- [x] Base the image on a slim Python 3 (stdlib only, D-10 — no `pip install`).
- [x] COPY `orchestrator/` into the image; run with `--ws` so TCP + WebSocket +
      HTTP all listen.
- [x] Entrypoint maps env vars -> CLI flags: `PORT`->`--port`, `WS_PORT`->
      `--ws-port`, `HTTP_PORT`->`--http-port`, `ADMIN_KEY`->`--admin-key`,
      `ROOM_TTL`->`--room-ttl`, `ROOMS_FILE`->`--rooms-file`, `HOST`->`--host`
      (default 0.0.0.0).
- [x] Sensible defaults matching the orchestrator (5005 / 5006 / 8080, ttl 600).
- [x] Orchestrator logs to stdout (container-friendly).

## Acceptance

`docker run` with no params starts the orchestrator on 5005/5006/8080; passing env
vars overrides each parameter (verified in the startup log line / `status.json`).

## Notes

`--ws` is required for the browser carrier (midi-maze-js connects over WebSocket).
