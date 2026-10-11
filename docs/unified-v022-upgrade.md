# Voltra Unified v0.22.0 + Mobile v1.4.0 — Upgrade & rollback

This release branch combines **Desktop Dashboard V3** (PR #8), the **Arabic/English locale and translated secondary pages from Dashboard V2** (PR #7), and a **Fast Control** implementation for backend/React/Flutter. Do not merge the old PRs independently over this branch.

## What is verified vs. what still requires hardware

GitHub Actions automatically type-checks/builds React, checks desktop/mobile/tablet UI, executes Python integration/unit tests, and builds/tests the Flutter Android APK. This proves the project builds and its mocked/protocol tests work, **not** that relays switch at a particular physical latency. Test a real strip before deploying to production.

Backend Fast Control does *not* make unverified acknowledgements look like confirmed relay state. It records:
- `metrics.last_control_ack_ms`: command through device ACK
- `metrics.last_control_total_ms`: through final verification
- `metrics.last_command_confirmed`: `true` only when `GETINFO` reports the target state

Background polling now skips a busy command session instead of queueing behind it. Default `VOLTRA_COMMAND_CONFIRM_DELAY` (0.15 s), response timeouts and retry limits are preserved for safety; do not tune before collecting hardware measurements.

Web and Android optimistic tiles visibly enter a pending state, re-check the server, and report errors. Bulk control executes one relay command per changed channel and refreshes once at the end. Android keeps the existing PIN/biometrics, HTTPS Bearer auth, LAN discovery, telemetry, schedules, countdowns and scenes.

## Updating an existing Docker installation

**Do not run `docker compose down -v`, `docker volume prune` or delete the Voltra data volume.** Back up server data and the configuration/token before changing anything.

In the existing server clone directory (the one containing `docker-compose.real.yml`):

```bash
# Save current production revision and a Docker copy of the data directory.
git rev-parse HEAD
BACKUP_DIR="$HOME/voltra-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
docker cp voltra:/app/data "$BACKUP_DIR/data"
test ! -f .env || cp .env "$BACKUP_DIR/voltra.env"

# Retrieve and checkout this integration branch.
git fetch origin feature/voltra-unified-fast-control
git switch -C feature/voltra-unified-fast-control --track origin/feature/voltra-unified-fast-control

# Review production settings and rebuild using the existing named volume.
docker compose -f docker-compose.real.yml config
docker compose -f docker-compose.real.yml up -d --build
docker compose -f docker-compose.real.yml ps
curl -fsS http://127.0.0.1:8086/health
```

If your production container isn't named `voltra`, replace it in `docker cp`; if Docker is listening on a different host HTTP port, adjust the health URL. The `git switch -C` command moves that local branch; ensure uncommitted local changes were backed up first. **Don't paste API tokens or `.env` into GitHub issues.**

### Safe staged acceptance

1. Confirm server health, that all expected strips and their mappings are preserved, and that the API auth token still works.
2. Open the web UI at `/voltra/` on a desktop; verify V3 navigation and Arabic/English toggle.
3. Open it on a phone; verify the original compact dashboard remains available.
4. With a low-risk test load, turn one physical outlet on/off on the server LAN and verify the appliance plus `metrics.last_command_confirmed`.
5. Test all four outlets, automation schedules, scene execution, remote HTTPS control and Android after a secure backup.
6. Compare command ACK and total times from real device metrics. Avoid assuming a fixed millisecond target.

### Rollback

If device control fails, switch back to the saved `git rev-parse HEAD` revision, then rebuild using the **same** compose file and Docker volume:

```bash
git switch --detach YOUR_SAVED_COMMIT_SHA
docker compose -f docker-compose.real.yml up -d --build
```

Only restore a saved data backup if necessary and after stopping the service. Never delete or overwrite a production volume as part of a normal rollback.

### CasaOS

For CasaOS, preserve its existing app's data bind mount or named volume, environment variables, access token, HTTP/TCP/UDP mappings and LAN-only device TCP port. Build the same branch into a custom image or update from its installation source. Do not apply the Docker CLI upgrade commands blindly to an unknown CasaOS-managed deployment.

## Mobile APK

The GitHub Actions `mobile-apk` workflow uploads `Voltra-Mobile-v1.4.0` with the APK, SHA256SUMS and BUILD-INFO. Pull request builds use **test signing**, so they might not install over a production-signed APK. Do not uninstall an existing app containing sensitive local settings without exporting its configuration. Production in-place upgrades need the **same signing keystore** used for the already installed APK. The package remains `com.ayman.voltra.voltra_mobile`.

## Files changed

- `frontend/src/desktop.tsx`, `desktop.css`: Desktop V3
- `frontend/src/i18n.ts`, `ui.tsx`, `views.tsx`: V2 language support
- `frontend/src/App.tsx`: optimistic control and bulk one-refresh
- `voltra_local/tcp_server.py`: telemetry polling priority and command timings
- `mobile/lib/app_controller.dart`, `main.dart`: verified optimistic state, pending control and dynamic provisioning IP
- Python, Playwright and Flutter tests.

The existing legacy console stays at `/voltra/legacy`. Physical device port 10086 and UDP 10087 should remain LAN-only.
