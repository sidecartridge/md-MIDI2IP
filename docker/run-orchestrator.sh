#!/bin/sh
# Map environment variables to orchestrator.py CLI flags (EPIC-17 / D-16) and run
# it. --ws is always enabled so the browser (midi-maze-js) WebSocket carrier works.
set -eu

ARGS="--host ${HOST:-0.0.0.0}"
ARGS="$ARGS --port ${PORT:-5005}"
ARGS="$ARGS --ws --ws-port ${WS_PORT:-5006}"
ARGS="$ARGS --http-port ${HTTP_PORT:-8080}"
ARGS="$ARGS --room-ttl ${ROOM_TTL:-600}"
[ -n "${ADMIN_KEY:-}" ] && ARGS="$ARGS --admin-key ${ADMIN_KEY}"
[ -n "${ROOMS_FILE:-}" ] && ARGS="$ARGS --rooms-file ${ROOMS_FILE}"

# orchestrator.py imports its local `ws` module from its own directory.
exec python3 /app/orchestrator/orchestrator.py $ARGS
