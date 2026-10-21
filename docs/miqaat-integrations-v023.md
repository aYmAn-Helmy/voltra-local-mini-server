# Voltra Miqaat v0.23.0 — High-priority IoT integrations

This is an **optional, LAN-only enhancement branch** based on `miqaat`.
It keeps the stock MTTL-W01 firmware and the existing CasaOS/Docker data volume,
Desktop V3 and the Android layout. Nothing is flashed onto a physical strip.

## Features and measured limitations

| Feature | Added | Notes |
|---|---|---|
| Real outlet amperage | Yes | Native `up:power_report:<1..4>:current` (mA). Voltage remains separate. Firmware must support the command. `null` means unavailable; **never** estimate amps as a measured value. |
| Total current | Yes | Only reported after **all four channels** have current measurements. |
| MQTT + Home Assistant Discovery | Optional | MQTT broker required, not bundled or exposed by default; auto-creates 4 switches + energy/power/current/temperature sensors, voltage, total amps, Wi-Fi RSSI and alert binary sensor. |
| Matter / Apple Home / Google Home | Optional adapter | Publish Matterbridge MQTT config/state/write topics. Requires **separate** Matterbridge + `matterbridge-mqtt` plugin and Matter-capable controller; pairing is not automatic or tested on physical controller. |
| Software safety alerts | Yes | Two different, recent sensor readings above a configured limit; SSE, REST `/voltra/api/alerts`, dashboard/Android warning and retained MQTT warning topic. Events also written to audit log. |
| Automated shutdown | **Disabled by default** | User can opt in through dashboard Settings. Attempts OFF on outlets 1–4, no safety guarantee. **This is not a certified overcurrent/overheat circuit protection mechanism.** |
| Stock native MTTL protocol | Preserved | Server retains 10086 TCP, 10087 UDP, existing Fast Control and confirmation behaviour. |

### Command timing and stale sensors

- Optional current readings are **sequential** with an 800 ms timeout per channel to limit interference with ON/OFF; background polling yields to pending user commands.
- Voltage and Wi-Fi status still use native diagnostics. Current values are shown only when reported, not inferred.
- The safety monitor rejects stale measurement timestamps (90 seconds), checks two **different measured samples** before alerting or optionally attempting shutdown.
- A successful device command ACK alone is not a verified relay switch. MQTT writes pass through the same backend GETINFO verification.
- Software shutdown can fail on Wi-Fi disconnection, firmware hang, server restart, or damaged hardware. Never replace the manufacturer's protection/fuse/circuit breaker.

## 1. Local Docker/CasaOS upgrade (preserve existing data)

Back up `/DATA/AppData/Voltra/data` (CasaOS) or the Docker named data volume,
the original Git SHA, and the existing environment file. **Never run `down -v`.**

From your existing repository checkout:

```bash
git fetch origin feature/miqaat-priority-integrations
git switch --track -c feature/miqaat-priority-integrations origin/feature/miqaat-priority-integrations
# If branch already exists locally: git switch feature/miqaat-priority-integrations && git pull --ff-only

# CasaOS build, preserving /DATA/AppData/Voltra/data:
docker compose --env-file .env.casaos -f docker-compose.casaos.build.yml up -d --build
# Standard Docker alternative: docker compose -f docker-compose.real.yml up -d --build
curl -fsS http://127.0.0.1:8086/health
```

The code changes remain on a **review branch** until manually merged. The container
should report version `0.23.0`; if the old build remains, verify that Docker
built the correct branch.

## 2. MQTT + Home Assistant

Use an MQTT broker running on your trusted LAN (for example, an authenticated
Mosquitto instance). The broker should require a password, restrict topic ACLs,
and should **not** be forwarded to the Internet. The Voltra HTTP server is
tokenless only within the LAN; enabling MQTT does not make an unauthenticated
public endpoint safe.

On CasaOS, add to the existing, untracked `.env.casaos` (not to a Git commit):

```dotenv
VOLTRA_MQTT_HOST=192.168.1.20
VOLTRA_MQTT_PORT=1883
VOLTRA_MQTT_USERNAME=voltra
VOLTRA_MQTT_PASSWORD=YOUR_PRIVATE_BROKER_PASSWORD
VOLTRA_MATTER_MQTT=0
```

Change `192.168.1.20` to **your MQTT broker**, not the strip or Voltra IP;
the sample address is only a placeholder. A broker host left empty disables
MQTT completely. Restart the CasaOS build using the command above.

In Home Assistant: Settings → Devices & Services → MQTT integration.
Enable automatic MQTT discovery. Managed strips then appear under the same
stable `voltra_<mac>` device identifier. Each has:
- switch: Outlet 1–4
- sensors: per-outlet measured current (A), watts, kWh, temperature; voltage,
  total current and Wi-Fi signal
- binary sensor: Power safety warning

Example raw topics:

```text
homeassistant/switch/voltra_d8aa59d28888_1/config
voltra/D8AA59D28888/outlet/1/state
voltra/D8AA59D28888/outlet/1/current_a
voltra/D8AA59D28888/outlet/1/set      # ON or OFF, not retained
voltra/D8AA59D28888/availability
voltra/D8AA59D28888/safety_warning
```

Do not retain commands to `.../set`: the bridge discards retained requests to
prevent stale replay after reconnect. It never sets confirmed ON based solely on
a broker acknowledgement.

## 3. Optional Matterbridge for Apple Home and Google Home

Matter support is an *adapter* through the existing MQTT broker. It does **not**
replace Voltra's firmware, TCP server or Android app.

1. Install the official [Matterbridge](https://github.com/Luligu/matterbridge)
   on a machine with the LAN multicast/mDNS and IPv6 networking required by
   your Matter controller.
2. In the Matterbridge frontend, install the
   [matterbridge-mqtt plugin](https://github.com/Luligu/matterbridge-mqtt).
3. Set the plugin broker URL, port, username/password and base topic:
   `matterbridge`. Ensure it uses the same broker as the Voltra server.
4. Set `VOLTRA_MATTER_MQTT=1` in the Voltra environment and rebuild/restart.
5. Matterbridge detects **four OnOffPlugInUnit endpoints per online managed strip**
   via retained `config`, `state` and `subscribe` topics.
6. Use the Matterbridge commissioning QR code in a compatible Apple Home /
   Google Home / SmartThings controller. Complete pairing in the platform UI.
7. Verify actions go through the Voltra TCP server and GETINFO confirms relay
   state; test Apple/Google behaviour on a private staging network.

Example Matterbridge topics:

```text
matterbridge/voltra_d8aa59d28888_outlet_1/config/root
matterbridge/voltra_d8aa59d28888_outlet_1/state/root
matterbridge/voltra_d8aa59d28888_outlet_1/subscribe/root
matterbridge/voltra_d8aa59d28888_outlet_1/write/root
```

Matter pairing/compatibility depends on the third-party plugin release,
the Matter controller and the network; no physical pairing has been proven by
our GitHub build or unit tests. **Do not pair the same outlets twice through both
Home Assistant and Matterbridge or you may see duplicate devices.**

## 4. Safety settings

Open Voltra Settings and edit:
- Power alert threshold (default **3000 W** per strip)
- Current alert threshold (default **12 A** total)
- Temperature alert threshold (default **75 °C** per outlet)
- Existing minimum/maximum voltage for voltage warnings
- Software shutdown: **Disabled (recommended)** or opt in to attempt turning
  all four outlets OFF after two distinct fresh high-load/high-heat samples.

The dashboard and Android app show active warnings; the alerts API is
`GET /voltra/api/alerts` (within the trusted LAN). Every warning is recorded
in the Audit log, and alert raised/cleared events reach SSE clients.

**Do not treat these controls as electrical protection:** native firmware
measurement latency, network connection and software failures can prevent or
delay shutdown. Leave real fuses/overload and thermal cutouts enabled.

## 5. Android v1.5.0

The existing Flutter app retains its screens and control functions, and now
shows per-outlet and total measured current and active safety warnings.
GitHub Actions builds `Voltra-Mobile-v1.5.0` for review of this PR, test-signed.
An in-place update needs the same signing certificate as the already installed
APK. Do not uninstall before saving local configuration.

## QA / rollback

CI validates Python 3.11/3.12, Docker/CasaOS and demo builds, frontend
TypeScript and Playwright on desktop/tablet/mobile. Android Analyze, Flutter
tests and APK release build run in the Android workflow.

Physical acceptance on one low-risk test strip is still mandatory:
1. Confirm native current readings vs a trustworthy external meter.
2. With no special broker installed, verify the unchanged normal dashboard
   and Android control/energy flows.
3. With a broker, verify automatic HA device discovery, a real ON/OFF command,
   and no duplicate triggers on MQTT reconnect.
4. With Matterbridge, verify pairing, on/off and state after a physical switch.
5. Test warnings with **simulated data first**, and verify that software
   shutdown is OFF by default. Avoid deliberate unsafe real overload tests.

Rollback: record the old commit SHA; after backup, switch to it and rebuild with
the same compose file and existing volume (never `down -v`).

Upstream Matterbridge MQTT protocol reference:
https://github.com/Luligu/matterbridge-mqtt
