#!/bin/sh
# Launch the md-MIDI2IP image with all default parameters; the only required
# argument is the admin key (it gates room provisioning over the REST API).
#
# Usage:   docker/run.sh <ADMIN_KEY>
# Override (optional, via env): IMAGE, NAME, VOLUME
#
# Defaults: ports 80 (web) / 5005 (game TCP) / 5006 (WebSocket) / 8080 (HTTP+REST),
# rooms persisted in the named volume at /data/rooms.json.
set -eu

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "usage: $0 <ADMIN_KEY>" >&2
  exit 1
fi
ADMIN_KEY="$1"

IMAGE="${IMAGE:-md-midi2ip}"
NAME="${NAME:-midi2ip}"
VOLUME="${VOLUME:-midi2ip-data}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "image '$IMAGE' not found — build it first from the repo root:" >&2
  echo "  docker build -f docker/Dockerfile -t $IMAGE ." >&2
  exit 1
fi

# Replace any previous container of the same name.
docker rm -f "$NAME" >/dev/null 2>&1 || true

exec docker run -d \
  --name "$NAME" \
  -p 80:80 -p 5005:5005 -p 5006:5006 -p 8080:8080 \
  -v "$VOLUME":/data \
  -e ADMIN_KEY="$ADMIN_KEY" \
  -e INSPECT="${INSPECT:-}" \
  --restart unless-stopped \
  "$IMAGE"
