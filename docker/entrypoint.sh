#!/bin/sh
# Pre-flight, then hand off to supervisord which runs nginx + the orchestrator.
set -eu

# Ensure the rooms-file directory exists (it's a mounted volume by default).
if [ -n "${ROOMS_FILE:-}" ]; then
  mkdir -p "$(dirname "$ROOMS_FILE")"
fi

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/midi2ip.conf
