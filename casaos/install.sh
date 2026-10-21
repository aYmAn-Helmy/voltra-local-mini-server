#!/usr/bin/env bash
set -euo pipefail

# Miqaat priority integrations: tokenless LAN-only Voltra with optional MQTT bridge.
SOURCE_BRANCH="feature/miqaat-priority-integrations"
COMPOSE_FILE="docker-compose.casaos.build.yml"
ENV_FILE=".env.casaos"
DATA_DIR="/DATA/AppData/Voltra/data"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Run this on the CasaOS host."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required."
  exit 1
fi

# Do not silently replace a modified checkout or switch back to main.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Uncommitted tracked changes exist. Back up/commit before installing miqaat."
    exit 1
  fi
  git fetch origin "$SOURCE_BRANCH"
  if [ "$(git branch --show-current)" != "$SOURCE_BRANCH" ]; then
    if git show-ref --verify --quiet "refs/heads/$SOURCE_BRANCH"; then
      git switch "$SOURCE_BRANCH"
    else
      git switch --track -c "$SOURCE_BRANCH" "origin/$SOURCE_BRANCH"
    fi
  fi
  git pull --ff-only origin "$SOURCE_BRANCH"
fi

mkdir -p "$DATA_DIR"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# Voltra Miqaat; no API token or public proxy configuration.
VOLTRA_TIMEZONE=Africa/Cairo
VOLTRA_POLL_INTERVAL=10
VOLTRA_DIAGNOSTICS_INTERVAL=30
VOLTRA_TELEMETRY_INTERVAL=60
EOF
  chmod 600 "$ENV_FILE"
  echo "Created tokenless local configuration: $ENV_FILE"
else
  echo "Preserving existing $ENV_FILE. Miqaat ignores any old API token and public-origin variables."
fi

# Keep /DATA/AppData/Voltra/data intact: NEVER run docker compose down -v.
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

HOST_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' || true)"
if [ -z "$HOST_IP" ]; then
  HOST_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | awk '/^127\./ {next} {print; exit}' || true)"
fi

echo
echo "Voltra Miqaat ready (LAN-only; no API token)."
echo "Dashboard: http://${HOST_IP:-CASAOS-IP}:8086/voltra/"
echo "Device TCP: ${HOST_IP:-CASAOS-IP}:10086"
echo "Discovery: UDP ${HOST_IP:-CASAOS-IP}:10087"
echo
echo "IMPORTANT: Disable any Internet-facing NAT/port forwarding or reverse proxy"
echo "that publishes Voltra. Use a VPN for remote access."
