# Voltra v0.22 - Standalone MTTL-W01 + Mosquitto on CasaOS

This version supports original TCP devices and standalone firmware 2.1.x via the *same* Voltra API.

## One-command update for an existing CasaOS source install

From the Voltra Git checkout, after the feature is merged to main:

```bash
sudo bash casaos/install.sh
```

The installer backs up /DATA/AppData/Voltra/data, preserves the existing API token,
creates a separate Mosquitto password database and volume in /DATA/AppData/Voltra/mosquitto,
and builds both containers. Never run docker compose down -v for upgrades.

On first install, view credentials locally (do not paste into chat):

```bash
sudo grep '^VOLTRA_MQTT_DEVICE_' .env.casaos
```

Use the CasaOS **LAN IP** for the device's MQTT broker host, TCP port 1883, username
voltra_device and the generated password. In the firmware MQTT page set Topic Prefix
to `voltra`, enable MQTT and save. Voltra server authenticates with a separate user.

Only 1883/TCP is published to the selected LAN IP. Do not port forward to WAN.
MQTT payloads are unencrypted and device access is not separated by per-device ACLs.

## Adding devices and local timers

1. Standalone device must be joined to LAN with NTP time set.
2. Enable MQTT pointing at the CasaOS broker.
3. Find new device in Voltra /voltra/ → Add strip. Approve it.
4. Control 4 outlets from the dashboard. On standalone devices, Timer settings
   are saved through MQTT /timerN/set to internal flash (0–1440 minutes).
5. Firmware's **Scheduler** remains device-owned, managed on the strip web page;
   this release does not copy Voltra server schedules to device flash.
6. For legacy original TCP devices, Voltra schedules still require the server.

Firmware topics: `voltra/standalone/<12-hex-mac>/availability`,
`/sw1`...`/sw4`, `/power`, `/meter`, `/timer1`...`/timer4`.
Commands: `/1/set`...`/4/set` and `/timer1/set`...`/timer4/set`.
Voltra always sends commands with retain=false and waits for an observed state report.

## Validation

```bash
docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml ps
docker logs --tail 60 voltra
docker logs --tail 60 voltra-mosquitto
```

Use `docker exec voltra-mosquitto mosquitto_sub -h 127.0.0.1 -u voltra -P "$PASSWORD" -t 'voltra/standalone/+/availability' -v`
with a password supplied securely in the current shell. Never paste credentials into logs.

If the server image fails after upgrade, keep the backup and previous Git revision
and rebuild the previous release. Do not delete data directories or clear volumes.
Real relay/schedule behavior must be smoke-tested on a noncritical load.
