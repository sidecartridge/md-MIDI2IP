# md-MIDI2IP — Docker deployment (EPIC-17)

A single image that hosts the whole server side:

- `orchestrator.py` — game **TCP :5005**, **WebSocket :5006**, **HTTP status + rooms REST :8080**
- **nginx** serving the `midi-maze-js` web app on **:80**

Both run under `supervisord`. Plain http/ws only (no TLS — terminate externally if
exposed, D-13). See `docs/epics/EPIC-17-dockerized-deployment/`.

`midi-maze-js` is a git submodule (built with Vite during the image build). The web
app auto-targets the orchestrator at `ws://<browser-host>:5006` and reads `/rooms`
from that same host:port, so **no per-deploy configuration is needed** — just open
the server's address in a browser.

## Layout

```
docker/
  Dockerfile            # build from the repo root: docker build -f docker/Dockerfile -t md-midi2ip .
  entrypoint.sh         # pre-flight, then exec supervisord
  run-orchestrator.sh   # maps env vars -> orchestrator.py CLI flags
  nginx/default.conf    # serve the static app on :80
  supervisor/supervisord.conf
  .env.example
.dockerignore           # (repo root) keeps the build context small
```

## Build & run

```sh
# from the repository root (clone with submodules, or: git submodule update --init)
docker build -f docker/Dockerfile -t md-midi2ip .

docker run -d --name midi2ip \
  -p 80:80 -p 5005:5005 -p 5006:5006 -p 8080:8080 \
  -v midi2ip-data:/data \
  --env-file docker/.env.example \
  md-midi2ip
```

- Browser: open `http://<host>/` — the app connects to `ws://<host>:5006` and lists
  rooms from `http://<host>:5006/rooms`.
- Hardware ST/Pico or Hatari: point at `<host>:5005` (TCP) or `<host>:5006` (ws).
- Rooms persist in the `midi2ip-data` volume (`/data/rooms.json`).

## Parameters

Every orchestrator parameter is set via an env var — see `.env.example`
(`HOST`, `PORT`, `WS_PORT`, `HTTP_PORT`, `ADMIN_KEY`, `ROOM_TTL`, `ROOMS_FILE`).

## Status

- [x] midi-maze-js submodule + Vite build wired into the image.
- [ ] Build + validate end to end (STORY-06).
