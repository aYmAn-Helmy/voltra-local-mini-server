# Voltra Miqaat — tokenless LAN server

Miqaat is based on `feature/voltra-unified-fast-control`: Voltra Server v0.22.0, Desktop Dashboard V3, bilingual Arabic/English web UI, Fast Control, and compatibility with Voltra Mobile v1.4.0.

## Important: local only

- **No API token** is needed. The server ignores any legacy `VOLTRA_API_TOKEN` environment variable; the Miqaat installer never generates one.
- The LAN-only HTTP guard checks the network peer IP, local Host header, forwarded headers, and browser Origin; browser CORS is disabled.
- **The guard is not a firewall** and cannot reliably tell whether a local reverse proxy is forwarding a remote client without forwarding metadata. Before installing, REMOVE any WAN-to-Voltra NAT/port-forward and disable the Voltra HTTPS reverse proxy on your router. Do not expose ports 8086, 10086 or 10087 to the Internet. For remote access, use a private VPN to the LAN.
- Other devices **on your trusted local network** can operate the outlets without login. Treat Wi-Fi guests and untrusted LAN clients accordingly.

## CasaOS installation / update

Run from the CasaOS Linux shell after backing up the current installation. The active data directory is usually `/DATA/AppData/Voltra/data`; verify it on your host before proceeding.

```bash
# On the CasaOS host, copy data and existing environment before any update.
BACKUP="$HOME/voltra-miqaat-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
sudo cp -a /DATA/AppData/Voltra/data "$BACKUP/data"
[ ! -f .env.casaos ] || cp -a .env.casaos "$BACKUP/env.casaos"
git rev-parse HEAD

# In the repo working directory, switch to the new branch:
git fetch origin miqaat
git switch --track -c miqaat origin/miqaat
# If the local miqaat branch already exists: git switch miqaat && git pull --ff-only

# Install via local Docker build (never GHCR latest).
bash casaos/install.sh
docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml ps
curl -fsS http://127.0.0.1:8086/health
```

**Do not use `docker compose down -v`, delete `/DATA/AppData/Voltra/data`, or discard your existing `.env.casaos` during upgrade.**

Fresh clone (instead of the existing checkout):

```bash
git clone --branch miqaat https://github.com/aYmAn-Helmy/voltra-local-mini-server.git
cd voltra-local-mini-server
bash casaos/install.sh
```

Dashboard: `http://CASAOS-LAN-IP:8086/voltra/`.

## Standard Docker installation

```bash
git fetch origin miqaat
git switch --track -c miqaat origin/miqaat
# Save data and .env before changing the running production container.
docker compose -f docker-compose.real.yml up -d --build
curl -fsS http://127.0.0.1:8086/health
```

The standard Docker compose uses its existing `voltra_data` persistent named volume. Never remove this volume. Miqaat does not require a `.env` for authentication. If your host already has one, server ignores the old token.

## Functional smoke check

1. On a trusted local computer, open `http://SERVER-LAN-IP:8086/voltra/` without a token.
2. On the original Android app, connect to `http://SERVER-LAN-IP:8086` and leave the Access Token field empty. Existing saved token values can be cleared in app setup if desired.
3. Ensure connected strips, device mappings, schedules, scenes and energy history are preserved.
4. Test a single low-risk outlet ON/OFF, then verify the physical relay and reported state. The Fast Control UI updates optimistically; the TCP backend must confirm via `GETINFO`.
5. Confirm remote public domain and router's external forwarded ports no longer reach the server. Test from mobile data outside the Wi-Fi network (the expected result is **no access**, unless connected through a private VPN).

## Revert

Save the original Git commit hash and the backups before upgrading. On failure, switch back to the exact saved Git commit and rebuild using the same compose file and data volume:

```bash
git switch --detach YOUR_PREVIOUS_COMMIT_SHA
docker compose -f docker-compose.real.yml up -d --build
```

For CasaOS use `docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml up -d --build` instead. A rollback to a token-protected release will require its previously configured API token to keep remote access secure.

## Tests

The CI test matrix includes Python backend tests (including no-token LAN admission and blocked proxy/public requests), React frontend build, Playwright responsive UI, Docker/CasaOS smoke tests and Android APK build on the unified release. Physical relay response times cannot be proven by software-only tests.
