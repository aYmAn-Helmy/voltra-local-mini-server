# Voltra Local Mini Server

Local-first server for LG U+ / TONLY MTTL-W01 smart power strips.

## Current release

**v0.18.0**

Key capabilities:

- Native TCP control on port 10086
- Reliable provisioning with independent setup connections and retries
- Voltage and Wi-Fi RSSI diagnostics
- Physical-button live events
- Recurring schedules, one-time timers, countdowns and an offline command queue
- Automation rules for offline, weak Wi-Fi, low power, and voltage thresholds
- Health score and command/reconnect metrics
- SSE live updates for the dashboard
- Local total/per-outlet energy telemetry, history and mobile chart data
- Backup/restore for Voltra configuration and automation
- Audit log and write rate limiting
- Separate TCP and HTTP bind addresses
- Tokenless standalone LAN dashboard/API
- Mobile-first dark smart-home dashboard with total-power hero, quick actions and search
- Reference-style strip cards with 2x2 outlet tiles and per-strip Turn all on/off controls
- Server-side Rooms, Favorites, ordering, Scenes and energy/alert settings
- Voltra-X LAN discovery on UDP 10087

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

## CasaOS quick install

The repository now includes a CasaOS-oriented deployment:

- `docker-compose.casaos.yml` — CasaOS metadata + prebuilt GHCR image
- `docker-compose.casaos.build.yml` — local build fallback
- `casaos/install.sh` — one-command local installer
- persistent data at `/DATA/AppData/Voltra/data`

Recommended first install on a CasaOS host:

```bash
git clone https://github.com/aYmAn-Helmy/voltra-local-mini-server.git
cd voltra-local-mini-server
chmod +x casaos/install.sh
./casaos/install.sh
```

The installer builds the image locally, starts the container, and prints the dashboard URL.

Dashboard:

```text
http://CASAOS-LAN-IP:8086/voltra
```

Physical strips connect to:

```text
CASAOS-LAN-IP:10086/TCP
```

Voltra-X discovers the server on:

```text
CASAOS-LAN-IP:10087/UDP
```

A multi-architecture image is also built for `amd64` and `arm64`:

```text
ghcr.io/ayman-helmy/voltra-local-mini-server:latest
```

If the GHCR package is private, authenticate Docker with a GitHub token that has
`read:packages`, or use the local-build installer above.

## Real hardware on CasaOS / Docker

For a real MTTL-W01 test, use the CasaOS/Docker host's **LAN IP** as the Voltra server IP.
Give that host a static address or DHCP reservation first.

Create the environment file:

```bash
cp .env.example .env
```

Then start:

```bash
docker compose -f docker-compose.real.yml up -d --build
```

Open the dashboard from another LAN device:

```text
http://CASAOS-LAN-IP:8086/voltra
```

The real strip must be able to reach:

```text
CASAOS-LAN-IP:10086/TCP
```

When provisioning a strip, store **CASAOS-LAN-IP** as its server IP. Do not use the
container's internal Docker address.

If the CasaOS host is Ethernet-only, the built-in web provisioning page cannot reach the
strip's temporary `TONLY_TAP_...` Wi-Fi AP by itself. In that case, connect a laptop to
the strip AP and run:

```bash
python -m voltra_local.provision_cli --server-ip CASAOS-LAN-IP --ssid "YOUR_2.4G_WIFI"
```

The Wi-Fi password is requested securely. The tool sends the server-IP command and Wi-Fi
command using separate setup connections. After provisioning, reconnect the laptop to the
normal LAN; the strip should connect directly to Voltra on TCP 10086.

Useful commands:

```bash
docker compose -f docker-compose.real.yml ps
docker compose -f docker-compose.real.yml logs -f
docker compose -f docker-compose.real.yml restart
docker compose -f docker-compose.real.yml down
```

Persistent data is kept in the `voltra_data` Docker volume.

## Run

```bash
python -m voltra_local.app
```

Defaults:

- Device TCP: `0.0.0.0:10086`
- Dashboard/API: `127.0.0.1:8086`
- Data directory: `./data`

Important environment variables:

- `VOLTRA_TCP_BIND`
- `VOLTRA_HTTP_BIND`
- `VOLTRA_TCP_PORT`
- `VOLTRA_HTTP_PORT`
- `VOLTRA_DISCOVERY_PORT`
- `VOLTRA_TIMEZONE`
- `VOLTRA_CORS_ORIGIN`
- `VOLTRA_POLL_INTERVAL`
- `VOLTRA_DIAGNOSTICS_INTERVAL`
- `VOLTRA_TELEMETRY_INTERVAL`
- `VOLTRA_COMMAND_ATTEMPTS`
- `VOLTRA_COMMAND_CONFIRM_DELAY`
- `VOLTRA_RATE_LIMIT_PER_MINUTE`
- `VOLTRA_DATA_DIR`

## API additions

- `GET /voltra/api/events` — SSE live event stream
- `GET /voltra/api/automation`
- `POST /voltra/api/schedules` — recurring or one-time schedule
- `POST /voltra/api/countdown`
- `DELETE /voltra/api/schedules/{id}`
- `POST /voltra/api/rules`
- `DELETE /voltra/api/rules/{id}`
- `DELETE /voltra/api/queue`
- `GET /voltra/api/energy?mac=...&hours=24&outlet=1`
- `GET /voltra/api/energy/history?mac=...&hours=24&outlet=1`
- `GET/POST/DELETE /voltra/api/scenes...`
- `PUT /voltra/api/strips/{mac}/preferences`
- `GET/PUT /voltra/api/settings`
- `GET /voltra/api/audit?limit=100`
- `GET /voltra/api/backup`
- `POST /voltra/api/restore`

## Tests

```bash
python -m unittest discover -s tests -v
```
