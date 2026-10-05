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

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Updating Voltra source from origin/main..."
  git fetch origin main
  git pull --ff-only origin main
fi

SOURCE_VERSION="$(python3 -c 'import pathlib,re; p=pathlib.Path("voltra_local/__init__.py").read_text(); m=re.search(r"__version__\\s*=\\s*[\"'\"]([^\"'\"]+)", p); print(m.group(1) if m else "unknown")')"
echo "Source version: $SOURCE_VERSION"

if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<EOF
VOLTRA_CORS_ORIGIN=*
VOLTRA_POLL_INTERVAL=10
VOLTRA_DIAGNOSTICS_INTERVAL=30
VOLTRA_TELEMETRY_INTERVAL=60
EOF
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE."
else
  sed -i '/^VOLTRA_API_TOKEN=/d' "$ENV_FILE" || true
  echo "Using existing $ENV_FILE (API token removed/ignored)."
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
echo
echo "Use the CasaOS LAN IP as server IP when provisioning MTTL-W01 strips."
