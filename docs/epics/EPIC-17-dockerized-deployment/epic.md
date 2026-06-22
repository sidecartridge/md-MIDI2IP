---
id: EPIC-17
iteration: 8
title: Dockerized deployment (orchestrator + midi-maze-js web app)
status: todo
---

## Goal

Ship a single, deployable Docker image that turns any server into a complete
MIDI-to-IP host: it runs the `orchestrator.py` server on all its ports and serves
the `midi-maze-js` browser game as a static site on port 80. After `docker run`,
a browser can load the game and play through the orchestrator, and remote hardware
(ST + Pico) or Hatari nodes can join the same rings over the network. The
orchestrator is configured through its existing CLI parameters.

## Scope

- In scope: a new top-level `docker/` folder with a Dockerfile and supporting
  config (nginx, supervisor, entrypoint); `midi-maze-js` added as a git submodule
  and served on :80; the orchestrator run with all listeners (`--ws`) bound to
  0.0.0.0; orchestrator parameters passed in at `docker run` time; provisioned
  rooms persisted to a file on a mounted volume (`--rooms-file`); ports 80 / 5005
  / 5006 / 8080 exposed; a usage/deploy README.
- Out of scope: TLS / `wss` (D-13 — terminate externally if needed); multi-service
  orchestration (k8s / multi-container compose as the deliverable); publishing the
  image to a registry / CI (a later epic); the midi-maze-js ring-desync bug
  (separate follow-up).

## Decisions (this epic) — see D-16

- **Single image**: both processes (nginx + orchestrator) under one small
  supervisor (supervisord or s6-overlay). One artifact to deploy.
- **Ports exposed directly**: `80` (static site), `5005` (game TCP), `5006`
  (WebSocket), `8080` (HTTP status + rooms REST). The browser connects straight to
  `:5006`/`:8080`; hardware/Hatari to `:5005`/`:5006`. No reverse proxy.
- **midi-maze-js via git submodule** in this repo (version-pinned). URL: _TBD
  (to be provided)_.
- **No TLS** — plain http/ws on :80 (D-13); terminate TLS at an external proxy if
  an exposed deployment needs it.
- **Config via environment variables** mapped to the orchestrator CLI by the
  entrypoint; provisioned rooms persisted to a file on a named volume.

## Stories

- STORY-01: Deploy folder skeleton + midi-maze-js submodule
- STORY-02: Orchestrator service layer + parameter passing
- STORY-03: Static web server (nginx) for midi-maze-js on :80 + runtime endpoint config
- STORY-04: Single-image process supervision + ports + logging
- STORY-05: Rooms persistence + configuration surface
- STORY-06: Build, validate end-to-end, and document deployment

## Notes

- Orchestrator CLI (`orchestrator/orchestrator.py`): `--host` (0.0.0.0), `--port`
  5005, `--ws` + `--ws-port` 5006, `--http-port` 8080, `--admin-key`, `--room-ttl`
  600, `--rooms-file` ("" = in-memory). `--ws` must be enabled so the browser
  carrier works.
- The browser only knows `ws://host:port`; the WS port already serves `/rooms`
  with a CORS header (EPIC-14), so the app can list rooms and open a WebSocket on
  the same host.
- The midi-maze-js orchestrator endpoint must be resolved at **runtime** (the
  deploy host is unknown at build time): derive the host from
  `window.location.hostname` + the fixed WS/REST ports, or generate a `config.js`
  at container start. Settled in STORY-03.
- The orchestrator is stdlib-only (D-10), so a slim Python base image suffices —
  no `pip install` step.
