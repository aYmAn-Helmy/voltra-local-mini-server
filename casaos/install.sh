#!/usr/bin/env bash
set -euo pipefail

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

mkdir -p "$DATA_DIR"

if [ ! -f "$ENV_FILE" ]; then
  if command -v openssl >/dev/null 2>&1; then
    TOKEN="$(openssl rand -hex 24)"
  else
    TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  fi
  cat > "$ENV_FILE" <<EOF
VOLTRA_API_TOKEN=$TOKEN
VOLTRA_CORS_ORIGIN=*
VOLTRA_POLL_INTERVAL=10
VOLTRA_DIAGNOSTICS_INTERVAL=30
VOLTRA_TELEMETRY_INTERVAL=60
EOF
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE with a new API token."
else
  echo "Using existing $ENV_FILE."
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
TOKEN="$(sed -n 's/^VOLTRA_API_TOKEN=//p' "$ENV_FILE" | head -n1)"

echo
echo "Voltra is starting."
echo "Dashboard: http://${HOST_IP:-CASAOS-IP}:8086/voltra"
echo "Device TCP: ${HOST_IP:-CASAOS-IP}:10086"
echo "API token: $TOKEN"
echo
echo "Use the CasaOS LAN IP as server IP when provisioning MTTL-W01 strips."
