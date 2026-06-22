---
id: STORY-03
epic: EPIC-17
title: Static web server (nginx) for midi-maze-js on :80 + runtime endpoint config
status: done
---

## Goal

nginx serves the midi-maze-js app on :80, and the app connects to the orchestrator
on this host without a rebuild per deployment.

## Tasks

- [x] Serve the midi-maze-js dist on :80 with nginx (multi-stage `npm build` if the
      app needs building, else copy static files).
- [x] Resolve the orchestrator endpoint at runtime: prefer deriving the host from
      `window.location.hostname` + the fixed WS/REST ports (5006 / 8080), or
      generate a `config.js` from env at container start. Document the mechanism.
- [x] Confirm the app can GET `/rooms` (CORS) and open the WebSocket to the same
      host (EPIC-14 — the WS port also serves `/rooms`).
- [x] nginx access/error logs to stdout/stderr.

## Acceptance

Browsing to `http://<host>/` loads the game; it lists rooms and connects to the
orchestrator WebSocket on `<host>` with no per-deploy rebuild.

## Notes

Ports are exposed directly (D-16), so the app targets `ws://<host>:5006` and
`http://<host>:8080` — no nginx WebSocket proxy needed.
