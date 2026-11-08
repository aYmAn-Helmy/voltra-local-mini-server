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
MQTT_ROOT="/DATA/AppData/Voltra/mosquitto"
mkdir -p "$MQTT_ROOT/config" "$MQTT_ROOT/data"
chmod 700 "$MQTT_ROOT/config"
chmod 700 "$MQTT_ROOT/data"
# The broker process runs as UID 1883 and must own the host directories.
chown -R 1883:1883 "$MQTT_ROOT/config" "$MQTT_ROOT/data"

# Preserve the original Voltra data before replacing the container.
BACKUP_DIR="/DATA/AppData/Voltra/backups"
mkdir -p "$BACKUP_DIR"
if [ -d "$DATA_DIR" ] && find "$DATA_DIR" -mindepth 1 -print -quit | grep -q .; then
  BACKUP_FILE="$BACKUP_DIR/pre-mqtt-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$BACKUP_FILE" -C "$DATA_DIR" .
  chmod 600 "$BACKUP_FILE"
  echo "Backed up existing Voltra data to $BACKUP_FILE"
fi

if [ "${CI:-}" != "true" ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
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

# Prepare MQTT credentials once, without putting passwords in Git.
# Only the device's LAN-facing port is published; control remains inside Docker.
HOST_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}')"
if [ -z "$HOST_IP" ]; then
  HOST_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | awk '/^127\./ {next} /^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\./ {next} {print;exit}')"
fi
if [ -z "$HOST_IP" ]; then
  echo "No LAN IP found. Cannot safely bind the MQTT listener."
  exit 1
fi
# Reject a public IP to avoid accidentally exposing plaintext MQTT on WAN.
if ! python3 - "$HOST_IP" <<'PY'
import ipaddress, sys
try:
    address = ipaddress.ip_address(sys.argv[1])
    valid = address.version == 4 and address.is_private and not address.is_loopback
except ValueError:
    valid = False
sys.exit(0 if valid else 1)
PY
then
  echo "MQTT must bind to a private IPv4 LAN address, not $HOST_IP"
  exit 1
fi
if ! grep -q '^VOLTRA_MQTT_DEVICE_PASSWORD=.' "$ENV_FILE"; then
  if [ -f "$MQTT_ROOT/config/passwords" ]; then
    echo "Password database exists but environment credentials are missing. Refusing to rotate credentials."
    exit 1
  fi
  SERVER_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  DEVICE_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  cat >> "$ENV_FILE" <<EOF
VOLTRA_MQTT_ENABLED=1
VOLTRA_MQTT_USERNAME=voltra
VOLTRA_MQTT_PASSWORD=$SERVER_PASSWORD
VOLTRA_MQTT_DEVICE_USERNAME=voltra_device
VOLTRA_MQTT_DEVICE_PASSWORD=$DEVICE_PASSWORD
VOLTRA_MQTT_TOPIC_PREFIX=voltra
VOLTRA_MQTT_HOST_BIND=$HOST_IP
EOF
  chmod 600 "$ENV_FILE"
  echo "Generated server and device MQTT credentials."
fi

# Load credentials from the root-owned file only; never log secrets.
set -a
# shellcheck disable=SC1090
. "./$ENV_FILE"
set +a
if [ -z "${VOLTRA_MQTT_PASSWORD:-}" ] || [ -z "${VOLTRA_MQTT_DEVICE_PASSWORD:-}" ]; then
  echo "MQTT credentials are missing from $ENV_FILE"
  exit 1
fi
if [ ! -f "$MQTT_ROOT/config/passwords" ]; then
  # The broker image supplies mosquitto_passwd. Build hashed passwords locally.
  docker run --rm -v "$MQTT_ROOT/config:/mosquitto/config" eclipse-mosquitto:2 \
    mosquitto_passwd -c -b /mosquitto/config/passwords "$VOLTRA_MQTT_USERNAME" "$VOLTRA_MQTT_PASSWORD"
  docker run --rm -v "$MQTT_ROOT/config:/mosquitto/config" eclipse-mosquitto:2 \
    mosquitto_passwd -b /mosquitto/config/passwords "$VOLTRA_MQTT_DEVICE_USERNAME" "$VOLTRA_MQTT_DEVICE_PASSWORD"
fi
cat > "$MQTT_ROOT/config/mosquitto.conf" <<'EOF'
listener 1883 0.0.0.0
allow_anonymous false
password_file /mosquitto/config/passwords
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF
chown -R 1883:1883 "$MQTT_ROOT/config" "$MQTT_ROOT/data"
chmod 640 "$MQTT_ROOT/config/passwords"
chmod 644 "$MQTT_ROOT/config/mosquitto.conf"
chmod 600 "$ENV_FILE"

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
echo "MQTT Broker (LAN only): ${VOLTRA_MQTT_HOST_BIND}:1883"
echo "MQTT device username: ${VOLTRA_MQTT_DEVICE_USERNAME}"
echo "Device password: read VOLTRA_MQTT_DEVICE_PASSWORD in $ENV_FILE (never share it)."
echo
echo "Use the CasaOS LAN IP as server IP when provisioning MTTL-W01 strips."
echo "Remote API token is stored in $ENV_FILE (mode 600)."
echo "View it locally with: grep '^VOLTRA_API_TOKEN=' $ENV_FILE"
