#!/usr/bin/env bash
# Deploy md-MIDI2IP to a remote Ubuntu server: build the image locally, install
# Docker on the server, open the firewall, load the image (save->load over SSH),
# and copy the launcher. It does NOT start the container — run run.sh afterward.
#
# Usage:    docker/deploy.sh <user@host>
#   The remote target is REQUIRED and must include the user (no default),
#   e.g. root@midimaze.sidecartridge.com
#
# Env overrides:
#   IMAGE       image name/tag      (default: md-midi2ip)
#   REMOTE_DIR  dir on the server   (default: /opt/midi2ip)
#   SSH_OPTS    extra ssh/scp opts  (default: -o StrictHostKeyChecking=accept-new)
set -euo pipefail

REMOTE="${1:-}"
if [ -z "$REMOTE" ]; then
  echo "usage: $(basename "$0") <user@host>   (e.g. ubuntu@midimaze.sidecartridge.com)" >&2
  exit 1
fi
case "$REMOTE" in
  *@*) : ;;  # user explicitly given
  *) echo "error: include the remote user explicitly as user@host (no default user)" >&2; exit 1 ;;
esac
IMAGE="${IMAGE:-md-midi2ip}"
REMOTE_DIR="${REMOTE_DIR:-/opt/midi2ip}"
SSH_OPTS="${SSH_OPTS:--o StrictHostKeyChecking=accept-new}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # repo root

echo "==> [1/5] Building $IMAGE locally"
docker build -f "$ROOT/docker/Dockerfile" -t "$IMAGE" "$ROOT"

echo "==> [2/5] Installing Docker on $REMOTE (if missing)"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$REMOTE" 'sh -s' <<'REMOTE'
set -e
if ! command -v docker >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y curl ca-certificates
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
docker --version
REMOTE

echo "==> [3/5] Opening firewall ports (ufw, if present)"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$REMOTE" 'sh -s' <<'REMOTE'
set -e
if command -v ufw >/dev/null 2>&1; then
  for p in 22 80 5005 5006 8080; do ufw allow "${p}/tcp" || true; done
  ufw status verbose | head -30 || true
else
  echo "ufw not installed; skipping (ensure 80/5005/5006/8080 are reachable)"
fi
REMOTE

echo "==> [4/5] Transferring image (save -> load, gzipped)"
# shellcheck disable=SC2086
docker save "$IMAGE" | gzip -c | ssh $SSH_OPTS "$REMOTE" 'gzip -dc | docker load'

echo "==> [5/5] Copying launcher + env example to $REMOTE_DIR"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$REMOTE" "mkdir -p '$REMOTE_DIR'"
# shellcheck disable=SC2086
scp $SSH_OPTS "$ROOT/docker/run.sh" "$ROOT/docker/.env.example" "$REMOTE:$REMOTE_DIR/"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$REMOTE" "chmod +x '$REMOTE_DIR/run.sh'"

cat <<DONE

Done. Docker + image '$IMAGE' are on $REMOTE and the launcher is in $REMOTE_DIR.
Start it on the server (admin key gates room provisioning):

  ssh $REMOTE '$REMOTE_DIR/run.sh <ADMIN_KEY>'

Then open  http://${REMOTE#*@}/  in a browser.
DONE
