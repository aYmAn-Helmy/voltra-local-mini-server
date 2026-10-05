# Voltra Local Mini Server

Local-first server for LG U+ / TONLY MTTL-W01 smart power strips.

## Current release

**v0.14.0**

Key capabilities:

- Native TCP control on port 10086
- Reliable provisioning with independent setup connections and retries
- Voltage and Wi-Fi RSSI diagnostics
- Physical-button live events
- Daily schedules and an offline command queue
- Automation rules for offline, weak Wi-Fi, low power, and voltage thresholds
- Health score and command/reconnect metrics
- SSE live updates for the dashboard
- Local energy telemetry and history summaries
- Backup/restore for Voltra configuration and automation
- Audit log and write rate limiting
- Separate TCP and HTTP bind addresses

## Quick demo with Docker

Run an isolated demo container with a built-in fake MTTL-W01 device:

```bash
docker compose -f docker-compose.demo.yml up --build
```

Then open:

```text
http://127.0.0.1:8086/voltra
```

The demo publishes only the dashboard port to localhost. Device TCP stays inside the
container, and demo data is stored in the dedicated `voltra_demo_data` Docker volume.

Stop the demo:

```bash
docker compose -f docker-compose.demo.yml down
```

Reset all demo data:

```bash
docker compose -f docker-compose.demo.yml down -v
```

The fake strip will appear in **Add Device / إضافة مشترك**. Adopt it to test outlet
control, voltage, Wi-Fi RSSI, energy telemetry, schedules, health, and live updates.

## Run

```bash
python -m voltra_local.app
```

Defaults:

- Device TCP: `0.0.0.0:10086`
- Dashboard/API: `127.0.0.1:8086`
- Data directory: `./data`

To expose the dashboard/API on a LAN, configure a token:

```bash
VOLTRA_HTTP_BIND=0.0.0.0
VOLTRA_API_TOKEN=replace-with-a-long-random-token
python -m voltra_local.app
```

Important environment variables:

- `VOLTRA_TCP_BIND`
- `VOLTRA_HTTP_BIND`
- `VOLTRA_TCP_PORT`
- `VOLTRA_HTTP_PORT`
- `VOLTRA_API_TOKEN`
- `VOLTRA_CORS_ORIGIN`
- `VOLTRA_POLL_INTERVAL`
- `VOLTRA_DIAGNOSTICS_INTERVAL`
- `VOLTRA_TELEMETRY_INTERVAL`
- `VOLTRA_COMMAND_ATTEMPTS`
- `VOLTRA_COMMAND_CONFIRM_DELAY`
- `VOLTRA_RATE_LIMIT_PER_MINUTE`
- `VOLTRA_DATA_DIR`

`VOLTRA_ALLOW_INSECURE_REMOTE=1` exists only for explicitly trusted environments. Remote HTTP binding without an API token is rejected by default.

## API additions

- `GET /voltra/api/events` — SSE live event stream
- `GET /voltra/api/automation`
- `POST /voltra/api/schedules`
- `DELETE /voltra/api/schedules/{id}`
- `POST /voltra/api/rules`
- `DELETE /voltra/api/rules/{id}`
- `DELETE /voltra/api/queue`
- `GET /voltra/api/energy?mac=...&hours=24`
- `GET /voltra/api/audit?limit=100`
- `GET /voltra/api/backup`
- `POST /voltra/api/restore`

## Tests

```bash
python -m unittest discover -s tests -v
```
