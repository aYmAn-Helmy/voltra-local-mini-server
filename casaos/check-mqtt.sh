#!/usr/bin/env bash
set -euo pipefail

# Run on a CasaOS host after installation; never prints any passwords.
ENV_FILE=".env.casaos"
COMPOSE="docker-compose.casaos.build.yml"
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Run sudo bash casaos/install.sh first." >&2
  exit 1
fi
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" config --quiet
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" ps
curl --fail --silent --show-error http://127.0.0.1:8086/health
echo
docker exec voltra-mosquitto sh -c "test -s /mosquitto/config/passwords"
docker exec voltra-mosquitto sh -c "test -s /mosquitto/config/mosquitto.conf"
docker inspect --format '{{.State.Health.Status}}' voltra
echo "Inspect Voltra dashboard, adopt the strip and test one noncritical outlet."
