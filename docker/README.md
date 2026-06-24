# md-MIDI2IP — Docker deployment (EPIC-17)

A single image that hosts the whole server side:

- `orchestrator.py` — game **TCP :5005**, **WebSocket :5006**, **HTTP status + rooms REST :8080**
- **nginx** serving the `midi-maze-js` web app on **:80**, and reverse-proxying the
  orchestrator so the app also works over port 80 alone (see *Single-port access*)

Both run under `supervisord`. Plain http/ws only (no TLS — terminate externally if
exposed, D-13). `midi-maze-js` is a git submodule, built with Vite during the image
build. See `docs/epics/EPIC-17-dockerized-deployment/`.

## Layout

```
docker/
  Dockerfile            # build from the repo root: docker build -f docker/Dockerfile -t md-midi2ip .
  entrypoint.sh         # pre-flight, then exec supervisord
  run-orchestrator.sh   # maps env vars -> orchestrator.py CLI flags
  run.sh                # launch the image locally (admin key only, all defaults)
  deploy.sh             # install Docker + load image + copy launcher on a remote server
  nginx/default.conf    # serve the app on :80 + proxy /ws and /rooms
  supervisor/supervisord.conf
  .env.example
.dockerignore           # (repo root) keeps the build context small
```

## Build & run (local)

```sh
# from the repository root (clone with submodules, or: git submodule update --init)
docker build -f docker/Dockerfile -t md-midi2ip .

# launch with all defaults — the only required argument is the admin key
docker/run.sh <ADMIN_KEY>

# ...or the explicit form:
docker run -d --name midi2ip \
  -p 80:80 -p 5005:5005 -p 5006:5006 -p 8080:8080 \
  -v midi2ip-data:/data -e ADMIN_KEY=<ADMIN_KEY> \
  md-midi2ip
```

- Browser: open `http://<host>/`. By default the app connects to `ws://<host>:5006`
  and lists rooms from `:5006/rooms`; for port-80-only setups point it at
  `ws://<host>/ws` (see below).
- Hardware ST/Pico or Hatari: point at `<host>:5005` (TCP) or `<host>:5006` (ws).
- Rooms persist in the `midi2ip-data` volume (`/data/rooms.json`).

## Remote deployment

`deploy.sh` provisions a fresh Ubuntu server end to end (build locally → install
Docker → open the firewall → load the image → copy the launcher). It does **not**
start the container; you run `run.sh` afterward. The target is a required argument
and must include the user:

```sh
docker/deploy.sh root@midimaze.sidecartridge.com
# then, on the server:
ssh root@midimaze.sidecartridge.com '/opt/midi2ip/run.sh <ADMIN_KEY>'
```

Env overrides: `IMAGE`, `REMOTE_DIR` (default `/opt/midi2ip`), `SSH_OPTS`.

## Single-port access (port 80 only)

nginx reverse-proxies the orchestrator so the whole app works over `:80` alone —
handy behind a domain/firewall that only allows 80/443:

- `ws://<host>/ws`      -> orchestrator WebSocket (`:5006`) — **WebSocket upgrades only**;
  a plain GET to `/ws` returns `426` (it does not expose the orchestrator's UI).
- `http://<host>/rooms` -> orchestrator rooms REST (`:8080`).

Point the app's connect screen at `ws://<host>/ws` and everything — game carrier +
room list — is same-origin on :80. The direct ports (`5005`/`5006`/`8080`) remain
exposed too. The orchestrator's own operator UI (its `/` status/ring screen,
`/lobby`, `/status.json`) is **not** served on :80 — reach it directly on `:8080`.

### Real client IPs behind the proxy

When a player connects through the bundled nginx (`/ws`), the orchestrator reports
the **real browser IP** in its console/telemetry/reverse-DNS (via `X-Real-IP` /
`X-Forwarded-For`). It only trusts those headers from the in-container proxy
(loopback peer), so a direct client to the exposed `:5006` cannot spoof its address.

## Performance / latency

- **Host networking (Linux):** `NETWORK=host docker/run.sh <ADMIN_KEY>` shares the
  host network stack (no Docker NAT/userland-proxy hop) for lowest latency / highest
  throughput. Ports bind directly on the host; `ufw` rules still apply.
- **nginx `/ws`** uses `proxy_buffering off` + `tcp_nodelay`, so MIDI frames are
  forwarded immediately.
- **Lowest-latency client path:** connect the browser directly to `ws://<host>:5006`
  (skip the `/ws` proxy hop); the proxy is the single-port convenience. Note: the
  dominant latency for the lock-step ring is the internet RTT between players and the
  server, which these tunings cannot change.

## Parameters

Every orchestrator parameter is an env var — see `.env.example`:

| Env | Flag | Default |
| --- | --- | --- |
| `HOST` | `--host` | `0.0.0.0` |
| `PORT` | `--port` | `5005` |
| `WS_PORT` | `--ws-port` (with `--ws`) | `5006` |
| `HTTP_PORT` | `--http-port` | `8080` |
| `ADMIN_KEY` | `--admin-key` | (empty → REST writes refused) |
| `ROOM_TTL` | `--room-ttl` | `600` |
| `ROOMS_FILE` | `--rooms-file` | `/data/rooms.json` |
| `INSPECT` | `--inspect` (verbose per-chunk trace) | off (`1/true/yes/on` to enable) |

`run.sh` passes `INSPECT` through, e.g. `INSPECT=1 docker/run.sh <ADMIN_KEY>`, then
watch with `docker logs -f midi2ip`.

## Provisioning rooms (admin)

Room writes require `ADMIN_KEY` (empty refuses writes). With it set:

```sh
# create / list / delete rooms over the REST API (host = the server)
curl -X POST   -H "X-Admin-Key: $ADMIN_KEY" -d '{"room":"ALPHA"}' http://<host>:8080/rooms
curl           http://<host>:8080/rooms
curl -X DELETE -H "X-Admin-Key: $ADMIN_KEY" http://<host>:8080/rooms/ALPHA
```

Provisioned rooms are written to `ROOMS_FILE` on the `/data` volume and reloaded on
restart.

## docker-compose (optional)

The deliverable is the single image, but compose is handy for a fixed deployment:

```yaml
services:
  midi2ip:
    build:
      context: .
      dockerfile: docker/Dockerfile
    image: md-midi2ip
    ports: ["80:80", "5005:5005", "5006:5006", "8080:8080"]
    volumes: ["midi2ip-data:/data"]
    env_file: [docker/.env.example]
    restart: unless-stopped
volumes:
  midi2ip-data:
```
