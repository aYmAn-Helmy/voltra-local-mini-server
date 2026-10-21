# Miqaat high-priority features

This branch extends Miqaat without changing the MTTL-W01's stock firmware.

## Native per-outlet current (amperes)

The server polls `up:power_report:<channel>:current` for channels 1–4 during diagnostics and exposes `current_a` on each outlet plus `total_current_a`. Missing responses remain unknown, not zero. The React and Flutter outlet cards display Amperes when measured. Real-device validation is mandatory: the wire-frame format shares `up:power_report:<channel>:<value>` with voltage, so interpretations depend on the requested command and validated range.

## Home Assistant MQTT (opt-in)

Configure a trusted LAN MQTT broker in the server's `.env` or `.env.casaos`:

```dotenv
VOLTRA_MQTT_HOST=192.168.1.10
VOLTRA_MQTT_PORT=1883
VOLTRA_MQTT_USERNAME=
VOLTRA_MQTT_PASSWORD=
VOLTRA_MQTT_TLS=0
```

Restart using the same Docker Compose file. With `VOLTRA_MQTT_HOST` empty, **no MQTT connection is attempted**. With a broker configured, the bridge advertises four switches plus total power/current/voltage and per-outlet current/power/energy/temperature sensors (23 entities per detected strip) via MQTT Discovery, publishes confirmed snapshot states, and receives outlet ON/OFF commands via `voltra/<MAC>/outlet/<channel>/set`.

The bridge honors server-side strip approval and control permissions. The MQTT broker MUST be accessible only to trusted clients; use dedicated credentials and TLS for broker connections across untrusted links. MQTT QoS is 0 in this first integration, and Home Assistant should treat device states as reported/last-seen rather than physical contact sensing. Test state synchronization, reconnects and hardware commands before production deployment.

## Health alerts and safety

A separate monitor publishes deduplicated `device_alert` events over existing SSE and records them to the existing audit log. Default advisory thresholds: 1,500 W (total), 12 A (total), 75 °C (per-outlet); settings `unusual_power_w`, `alert_current_a`, `alert_temperature_c` can adjust them.

**These are notifications only** and depend on potentially delayed telemetry. There is NO automatic current/power cutoff in this release and no claim of certified overcurrent/overtemperature protection. Use proper hardware overload/RCD/circuit protection. Real protective disconnection is a separate firmware/hardware feature requiring lab tests; arbitrary relay commands are not a safe substitute.

## Matter

A production-quality native Matter bridge is **not included in this branch**. The direct MQTT→Home Assistant integration is implemented first and provides a stable path to future Matter/SmartThings interoperability. Matter commissioning requires a certified-compatible bridge stack and supported controller/network setup; no automatic native Matter pairing is claimed.

## CI and rollout

Run Python tests, React build, UI end-to-end tests, Docker smoke, and Android CI. Review this branch as a Draft PR targeting `miqaat`. Existing CasaOS data at `/DATA/AppData/Voltra/data` remains in place, and no API token is added to Miqaat. All physical ON/OFF and current sensor accuracy checks must be completed using a real test strip.

Use `docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml up -d --build` for CasaOS or `docker compose -f docker-compose.real.yml up -d --build` for normal Docker, after taking a backup.
