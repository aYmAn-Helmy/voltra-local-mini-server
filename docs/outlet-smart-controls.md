# Voltra Smart Outlets — Server v0.23.0 + Android v1.5.0

This branch, `feature/outlet-smart-controls-v1`, builds on the combined Desktop V3 + Arabic/English + Fast Control release branch.

## Actually implemented

Each MTTL-W01 relay/outlet has **server-side persistent** preferences (UTF-8 Arabic and English names, icon, power-off protection, lock, local activity notifications, restart policy, auto-off countdown, low-power off, and high-power alerts). Preferences appear in the ordinary /voltra/api/overview snapshot, including offline strips, and survive the existing full backup/export/restore.

Available from **Desktop V3 and mobile-browser dashboard** via the cog on each outlet; from **Flutter v1.5.0** via the outlet cog/long press:
- Customize outlet name and icon.
- Inspect current watts, last-24-hour and last-30-day consumption/cost estimates using real telemetry and configured EGP/kWh price. Sampling accuracy depends on strip reporting.
- Add, list and remove weekly schedules, set quick delayed ON or OFF, enable automatic OFF after an ON, configure sustained low-power shutoff and high-power alert thresholds.
- Prevent accidental power-off (explicit confirmation) and lock/unlock outlet control.
- Choose `none` (default and safest), `off`, or `last` on **reconnect to the server**, after an actual GETINFO. This is not a firmware setting for power outages.
- Create quick one-outlet scenes and execute scenes from existing Automation screens. A scene can combine multiple outlets via server API.
- Open outlet activity logs and read foreground mobile notifications. The Android notification drawer is fed from the audited server activity while the app is open. **No guaranteed system push notifications when the app is killed or the phone offline.**

Safety rules are enforced in `OutletManager` on server-side manual commands, scenes, PlayStation mappings, automated rules and both namespaced/legacy device API entry points. Locked outlets reject all commands. Protected outlets require `confirm_protected:true` for manual OFF and block automated OFF; incompatible protected+auto-off configurations return validation errors. Error responses are explicit; the UI does not assume an ACK means an electrically verified relay state.

**No new ports, protocol changes or cloud dependence.** The existing device TCP 10086 and discovery UDP 10087 stay private on LAN.

## Server upgrade on CasaOS

On the existing CasaOS host, identify the actual cloned repository and compose file before running anything. In the repo checkout, back up persistent data, `.env.casaos`, and the old commit. Never use `docker compose down -v` or delete `/DATA/AppData/Voltra/data`.

```bash
git rev-parse HEAD
sudo tar -C /DATA/AppData/Voltra -czf "$HOME/voltra-data-before-smart-outlets.tgz" data
cp .env.casaos "$HOME/voltra-env-before-smart-outlets"
git fetch origin feature/outlet-smart-controls-v1
git switch -c feature/outlet-smart-controls-v1 --track origin/feature/outlet-smart-controls-v1

# Keep existing environment and data bind mount. Build from this branch:
docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml up -d --build
docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml ps
curl -fsS http://127.0.0.1:8086/health
```

If the branch already exists locally, `git switch feature/outlet-smart-controls-v1 && git pull --ff-only` after fetching. If the installation uses the prebuilt `docker-compose.casaos.yml` pointing at `ghcr.io/...:latest`, that image will **not** contain the branch: switch to the **build** compose file and preserve the old data mount and security environment. Production remote HTTPS config/authorization should remain unchanged.

For ordinary Docker deployment, use the existing `docker-compose.real.yml` from this same branch, after backing up the named data volume and `.env`. See `docs/unified-v022-upgrade.md` for the existing rollback procedure.

## Android update

From the GitHub Actions `mobile-apk` workflow for this branch, download **Voltra-Mobile-v1.5.0**. It includes the `.apk` (test-signed for PR), `SHA256SUMS.txt`, and signing details. Package ID stays `com.ayman.voltra.voltra_mobile`; a release may only be installed as an in-place update when signed by the **same key** as the installed app. Don't uninstall an existing authenticated app until its connection details are securely backed up.

The Android API and Flutter tests, release build and an Android emulator startup smoke test must succeed before anyone treats it as candidate-ready.

## Validation checklist before production

1. Test a physical spare MTTL-W01 on the LAN (low-risk load only), verify command ACK and GETINFO state.
2. Change a strip name and all four outlet names in Arabic on Android, reopen both Android and desktop dashboard, verify identical text, icons and mappings.
3. Verify a locked outlet cannot be operated from Android, browser, scene or automation; verify protected OFF confirmation and automated OFF rejection.
4. Test a quick 1-minute timer and a recurring schedule with the correct **server timezone** (Africa/Cairo), including restart and reconnect.
5. Test configured auto-off / low-power threshold with measured watts, power alert and audit stream, both online and offline.
6. Test `none` as reconnect default; test `last` only with a harmless appliance. Never enable automatic re-energizing of heaters, PS5s/PCs or high-risk loads without a safety review.
7. Test LAN, remote HTTPS, token auth, saved PIN/biometric settings and a rollback on preserved data.

All hardware-dependent features are subject to firmware behaviors; automated checks validate mocked protocol, API and UI logic, not physical relay timing.

## API

- `GET/PUT /voltra/api/strips/<MAC>/outlets/<1..4>/preferences` — persisted settings
- `GET /voltra/api/strips/<MAC>/outlets/<1..4>/activity` — recent outlet activity
- `POST /voltra/api/strips/<MAC>/outlets/<1..4>/state` — `{"on":false,"confirm_protected":true}` for protected manual OFF
- `POST /voltra/api/schedules`, `POST /voltra/api/countdown`, `DELETE /voltra/api/schedules/<id>`
- `POST /voltra/api/scenes`, `POST /voltra/api/scenes/<id>/run`
- `GET /voltra/api/energy?mac=<MAC>&hours=24&outlet=1`, `GET /voltra/api/audit`

The auto-off timer and threshold rules are persisted as `managed_key`-tagged schedules/rules. They survive restarts and can be reconfigured without accumulating duplicates.

### Rollback

Record the old revision before switching, then (for the same CasaOS installation) use `git switch --detach YOUR_SAVED_SHA` and rebuild with `docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml up -d --build`. Keep the same data bind mount and security configuration. Restoring a pre-upgrade backup is only necessary if rollback fails to read the preserved JSON data; never wipe the volume as part of routine rollback.
