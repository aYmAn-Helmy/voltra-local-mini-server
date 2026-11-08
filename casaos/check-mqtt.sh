#!/usr/bin/env bash
set -euo pipefail

# Run as root on the CasaOS host. No credentials are printed.
ENV_FILE=".env.casaos"
COMPOSE_FILE="docker-compose.casaos.build.yml"
if [ ! -r "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Run sudo bash casaos/install.sh first." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
. "./$ENV_FILE"
set +a

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

ok=0
for i in $(seq 1 40); do
  if curl -fsS --max-time 2 http://127.0.0.1:8086/health >/dev/null; then
    ok=1
    break
  fi
  sleep 1
done
if [ "$ok" != "1" ]; then
  echo "Voltra HTTP health check failed" >&2
  exit 1
fi

docker exec voltra-mosquitto sh -c "test -s /mosquitto/config/passwords"
docker exec voltra-mosquitto sh -c "test -s /mosquitto/config/mosquitto.conf"
docker exec voltra-mosquitto mosquitto_pub -h 127.0.0.1 -p 1883 \
  -u "$VOLTRA_MQTT_USERNAME" -P "$VOLTRA_MQTT_PASSWORD" \
  -t "voltra/system/healthcheck" -m "ok"
curl -fsS --max-time 3 -H "Authorization: Bearer $VOLTRA_API_TOKEN" \
  http://127.0.0.1:8086/voltra/api/overview >/dev/null

status="starting"
for i in $(seq 1 40); do
  status="$(docker inspect --format '{{.State.Health.Status}}' voltra)"
  [ "$status" = "healthy" ] && break
  sleep 1
done
if [ "$status" != "healthy" ]; then
  echo "Voltra container health status: $status" >&2
  exit 1
fi
echo "OK: Voltra HTTP, authenticated API, and Mosquitto all operational."
