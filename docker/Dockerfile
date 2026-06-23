# md-MIDI2IP all-in-one deployment image (EPIC-17).
# Runs orchestrator.py (game TCP 5005, WebSocket 5006, HTTP/REST 8080) AND serves
# the midi-maze-js web app on :80, both under supervisord.
#
# Build from the REPO ROOT so the context sees orchestrator/ and the submodule:
#   docker build -f docker/Dockerfile -t md-midi2ip .

# ---- midi-maze-js build stage (Vite + TypeScript) -----------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY midi-maze-js/ ./
RUN npm ci && npm run build          # tsc --noEmit && vite build -> /web/dist

# ---- runtime: orchestrator (Python stdlib) + nginx + supervisor ---------------
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx supervisor curl \
 && rm -rf /var/lib/apt/lists/* \
 && ln -sf /dev/stdout /var/log/nginx/access.log \
 && ln -sf /dev/stderr /var/log/nginx/error.log

# Orchestrator — stdlib only, no pip deps (D-10).
COPY orchestrator/ /app/orchestrator/

# Static web app (built midi-maze-js) served by nginx on :80. The app derives the
# orchestrator endpoint at runtime from the browser host: ws://<host>:5006 (+ /rooms
# on the same host:port), so no per-deploy rebuild or proxy is needed (D-16).
COPY --from=web /web/dist/ /usr/share/nginx/html/

# nginx + supervisor + launch scripts
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default
COPY docker/supervisor/supervisord.conf /etc/supervisor/conf.d/midi2ip.conf
COPY docker/run-orchestrator.sh /app/run-orchestrator.sh
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /app/run-orchestrator.sh /entrypoint.sh

# Provisioned rooms persist on a volume (D-16).
ENV ROOMS_FILE=/data/rooms.json
VOLUME ["/data"]

# 80 static · 5005 game TCP · 5006 WebSocket · 8080 HTTP status/REST
EXPOSE 80 5005 5006 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/rooms" >/dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
