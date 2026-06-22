# md-MIDI2IP all-in-one deployment image (EPIC-17).
# Runs orchestrator.py (game TCP 5005, WebSocket 5006, HTTP/REST 8080) AND serves
# the midi-maze-js web app on :80, both under supervisord.
#
# Build from the REPO ROOT so the context sees orchestrator/ and the submodule:
#   docker build -f docker/Dockerfile -t md-midi2ip .

# ---- midi-maze-js build stage (STORY-03) --------------------------------------
# Enable once the midi-maze-js submodule + its build system are wired in.
# If the app needs a build:
#   FROM node:20-slim AS web
#   WORKDIR /web
#   COPY midi-maze-js/ ./
#   RUN npm ci && npm run build            # produces /web/dist
# If it ships prebuilt static files, skip this stage and COPY them in the runtime
# stage instead.

# ---- runtime: orchestrator (Python stdlib) + nginx + supervisor ---------------
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx supervisor curl \
 && rm -rf /var/lib/apt/lists/*

# Orchestrator — stdlib only, no pip deps (D-10).
COPY orchestrator/ /app/orchestrator/

# Static web app served by nginx on :80.
# TODO(STORY-03): replace the placeholder with the built midi-maze-js once the
# submodule lands, e.g.:
#   COPY --from=web /web/dist/ /usr/share/nginx/html/
#   # or, if prebuilt:  COPY midi-maze-js/ /usr/share/nginx/html/
COPY docker/web-placeholder/ /usr/share/nginx/html/

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
