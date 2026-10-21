"""Optional MQTT Home Assistant bridge for stock-firmware MTTL-W01 devices.

Requires paho-mqtt 2.x only when VOLTRA_MQTT_HOST is set.
No broker/external network is required for normal Voltra control.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from typing import Callable

_LOG = logging.getLogger(__name__)
_MAC = re.compile(r"^[0-9A-F]{12}$")


class MQTTBridge:
    def __init__(self, host: str, port: int, snapshot_provider: Callable[[], list[dict]],
                 command_executor: Callable[[str, int, bool], dict], *,
                 username: str = "", password: str = "", prefix: str = "voltra",
                 tls: bool = False, interval: float = 10.0):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.prefix = prefix.strip("/") or "voltra"
        self.tls = tls
        self.interval = max(2.0, interval)
        self.snapshot_provider = snapshot_provider
        self.command_executor = command_executor
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._client = None
        self._discovered: set[str] = set()
        self._connected = False

    def start(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("Install paho-mqtt>=2.0 for VOLTRA_MQTT_HOST integration") from exc
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="voltra-ha-bridge")
        if self.username:
            client.username_pw_set(self.username, self.password)
        if self.tls:
            client.tls_set()
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client
        client.connect_async(self.host, self.port, 30)
        client.loop_start()
        self._thread = threading.Thread(target=self._loop, name="voltra-mqtt", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._client:
            self._client.disconnect()
            self._client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self._connected = not reason_code.is_failure
        if self._connected:
            self._discovered.clear()
            client.subscribe(f"{self.prefix}/+/outlet/+/set")
        else:
            _LOG.warning("MQTT connection rejected: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False

    def _on_message(self, client, userdata, message):
        parts = message.topic.split("/")
        if len(parts) != 5 or parts[0] != self.prefix or parts[2] != "outlet" or parts[4] != "set":
            return
        mac, outlet_raw = parts[1].upper(), parts[3]
        if not _MAC.fullmatch(mac) or outlet_raw not in {"1", "2", "3", "4"}:
            return
        if message.payload not in (b"ON", b"OFF"):
            return
        # Never publish optimistic state from an MQTT command; report the verified state.
        def command():
            try:
                self.command_executor(mac, int(outlet_raw), message.payload == b"ON")
            except (KeyError, RuntimeError, TimeoutError, ValueError, OSError) as exc:
                _LOG.warning("MQTT outlet command failed (%s:%s): %s", mac, outlet_raw, exc)
            finally:
                self.publish_snapshot()
        threading.Thread(target=command, daemon=True, name="voltra-mqtt-command").start()

    def _send(self, topic: str, value, *, retain: bool = False):
        if self._connected and self._client:
            self._client.publish(topic, value, qos=0, retain=retain)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.publish_snapshot()
            except Exception:
                _LOG.exception("MQTT telemetry publication failed")
            self._stop.wait(self.interval)

    def publish_snapshot(self):
        if not self._connected:
            return
        for strip in self.snapshot_provider():
            mac = str(strip.get("mac") or "").upper()
            if not _MAC.fullmatch(mac):
                continue
            root = f"{self.prefix}/{mac}"
            online = bool(strip.get("online"))
            device = {"identifiers": [f"voltra_{mac}"], "name": f"Voltra {mac[-4:]}", "manufacturer": "LG U+", "model": "MTTL-W01"}
            if mac not in self._discovered:
                for ch in range(1, 5):
                    self._send(
                        f"homeassistant/switch/voltra_{mac}_{ch}/config",
                        json.dumps({"name": f"Outlet {ch}", "unique_id": f"voltra_{mac}_outlet_{ch}",
                            "state_topic": f"{root}/outlet/{ch}/state",
                            "command_topic": f"{root}/outlet/{ch}/set",
                            "availability_topic": f"{root}/availability",
                            "payload_on": "ON", "payload_off": "OFF", "device": device}),
                        retain=True,
                    )
                for ch in range(1, 5):
                    for slug, name, unit, device_class in [
                        ("current", "Current", "A", "current"),
                        ("power", "Power", "W", "power"),
                        ("energy", "Energy", "kWh", "energy"),
                        ("temperature", "Temperature", "°C", "temperature"),
                    ]:
                        self._send(
                            f"homeassistant/sensor/voltra_{mac}_{ch}_{slug}/config",
                            json.dumps({"name": f"Outlet {ch} {name}",
                                "unique_id": f"voltra_{mac}_outlet_{ch}_{slug}",
                                "state_topic": f"{root}/outlet/{ch}/{slug}",
                                "availability_topic": f"{root}/availability",
                                "unit_of_measurement": unit,
                                "device_class": device_class,
                                "state_class": "total_increasing" if slug == "energy" else "measurement",
                                "device": device}),
                            retain=True,
                        )
                for slug, name, unit, device_class in [
                    ("voltage", "Voltage", "V", "voltage"),
                    ("current", "Total Current", "A", "current"),
                    ("power", "Total Power", "W", "power"),
                ]:
                    self._send(
                        f"homeassistant/sensor/voltra_{mac}_{slug}/config",
                        json.dumps({"name": name, "unique_id": f"voltra_{mac}_{slug}",
                            "state_topic": f"{root}/sensor/{slug}",
                            "availability_topic": f"{root}/availability",
                            "unit_of_measurement": unit, "device_class": device_class, "device": device}),
                        retain=True,
                    )
                self._discovered.add(mac)
            self._send(f"{root}/availability", "online" if online else "offline", retain=True)
            if not online:
                continue
            for outlet in strip.get("outlets") or []:
                ch = outlet.get("channel")
                if ch not in (1, 2, 3, 4):
                    continue
                self._send(f"{root}/outlet/{ch}/state", "ON" if outlet.get("relay") else "OFF", retain=True)
                for slug, field in [
                    ("current", "current_a"),
                    ("power", "power_w"),
                    ("energy", "energy_kwh"),
                    ("temperature", "temperature_c"),
                ]:
                    value = outlet.get(field)
                    if value is not None:
                        self._send(f"{root}/outlet/{ch}/{slug}", str(value), retain=True)
            for slug, value in [
                ("voltage", strip.get("voltage_v")),
                ("current", strip.get("total_current_a")),
                ("power", sum(float(o.get("power_w") or 0) for o in strip.get("outlets") or [])),
            ]:
                if value is not None:
                    self._send(f"{root}/sensor/{slug}", str(value), retain=True)
