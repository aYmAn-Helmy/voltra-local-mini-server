#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.casaos.build.yml"
ENV_FILE=".env.casaos"
DATA_DIR="/DATA/AppData/Voltra/data"
PUBLIC_ORIGIN="https://b8710ce04869.sn.mynetname.net"
TRUSTED_PROXY="192.168.1.7/32"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Run this on the CasaOS host."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required to generate the Voltra API token."
  exit 1
fi

mkdir -p "$DATA_DIR"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Updating Voltra source from origin/main..."
  git fetch origin main
  git pull --ff-only origin main
fi

SOURCE_VERSION="$(sed -n 's/^__version__ = "\\(.*\\)"/\\1/p' voltra_local/__init__.py | head -n1)"
echo "Source version: ${SOURCE_VERSION:-unknown}"

if [ ! -f "$ENV_FILE" ]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  cat > "$ENV_FILE" <<EOF
VOLTRA_API_TOKEN=$TOKEN
VOLTRA_TRUSTED_PROXY=$TRUSTED_PROXY
VOLTRA_PUBLIC_ORIGIN=$PUBLIC_ORIGIN
VOLTRA_CORS_ORIGIN=$PUBLIC_ORIGIN
VOLTRA_POLL_INTERVAL=10
VOLTRA_DIAGNOSTICS_INTERVAL=30
VOLTRA_TELEMETRY_INTERVAL=60
VOLTRA_TIMEZONE=Africa/Cairo
VOLTRA_DISCOVERY_PORT=10087
EOF
  chmod 600 "$ENV_FILE"
  echo "Created secure $ENV_FILE with a random API token."
else
  if ! grep -q '^VOLTRA_API_TOKEN=.' "$ENV_FILE"; then
    TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    printf '\nVOLTRA_API_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
    echo "Added a random API token to existing $ENV_FILE."
  fi
  if ! grep -q '^VOLTRA_TRUSTED_PROXY=' "$ENV_FILE"; then
    printf 'VOLTRA_TRUSTED_PROXY=%s\n' "$TRUSTED_PROXY" >> "$ENV_FILE"
  fi
  if ! grep -q '^VOLTRA_PUBLIC_ORIGIN=' "$ENV_FILE"; then
    printf 'VOLTRA_PUBLIC_ORIGIN=%s\n' "$PUBLIC_ORIGIN" >> "$ENV_FILE"
  fi
  if grep -Fxq 'VOLTRA_CORS_ORIGIN=*' "$ENV_FILE"; then
    sed -i "s#^VOLTRA_CORS_ORIGIN=\\*$#VOLTRA_CORS_ORIGIN=$PUBLIC_ORIGIN#" "$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE"
  echo "Using existing $ENV_FILE with secure remote-access migration."
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

HOST_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}')"
if [ -z "$HOST_IP" ]; then
  HOST_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | awk '
    /^127\./ {next}
    /^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\./ {next}
    {print; exit}
  ')"
fi

echo
echo "Voltra is starting."
echo "Dashboard: http://${HOST_IP:-CASAOS-IP}:8086/voltra"
echo "Device TCP: ${HOST_IP:-CASAOS-IP}:10086"
echo "Voltra-X Discovery: UDP ${HOST_IP:-CASAOS-IP}:10087"
echo
echo "Use the CasaOS LAN IP as server IP when provisioning MTTL-W01 strips."
echo "Remote API token is stored in $ENV_FILE (mode 600)."
echo "View it locally with: grep '^VOLTRA_API_TOKEN=' $ENV_FILE"
