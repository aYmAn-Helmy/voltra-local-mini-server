"""Optional LAN MQTT bridge for Home Assistant Discovery and Matterbridge MQTT.

MQTT is disabled unless VOLTRA_MQTT_HOST is configured. Commands are accepted
only for managed enabled strips and executed with the existing verified TCP path.
"""
from __future__ import annotations

import json
import queue
import re
import threading
from typing import Callable

MAC_RE = re.compile(r"^[0-9A-F]{12}$")
COMMAND_TOPIC_RE = re.compile(r"^voltra/([0-9A-F]{12})/outlet/([1-4])/set$")
MATTER_WRITE_RE = re.compile(r"^matterbridge/(voltra_([0-9a-f]{12})_outlet_([1-4]))/write/root$")


def discovery_messages(strip: dict) -> dict[str, dict]:
    """Home Assistant MQTT discovery: stable grouped identities and device sensors."""
    mac = str(strip["mac"]).upper()
    if not MAC_RE.fullmatch(mac):
        raise ValueError("invalid strip MAC")
    name = str(strip.get("name") or "Voltra " + mac[-4:])
    root = f"voltra/{mac}"
    device = {"identifiers": ["voltra_" + mac.lower()], "name": name,
              "manufacturer": "LG U+ / Jinheung", "model": str(strip.get("model") or "MTTL-W01"),
              "sw_version": str(strip.get("firmware_version") or "")}
    online = {"availability_topic": root + "/availability",
              "payload_available": "online", "payload_not_available": "offline"}
    messages: dict[str, dict] = {}
    for channel in range(1, 5):
        base = f"voltra_{mac.lower()}_{channel}"
        messages[f"homeassistant/switch/{base}/config"] = {
            "name": f"Outlet {channel}", "unique_id": base + "_switch",
            "state_topic": root + f"/outlet/{channel}/state",
            "command_topic": root + f"/outlet/{channel}/set",
            "payload_on": "ON", "payload_off": "OFF", "state_on": "ON", "state_off": "OFF",
            "device": device, **online,
        }
        for key, label, unit, devclass, stateclass in (
            ("power_w", "Power", "W", "power", "measurement"),
            ("current_a", "Current", "A", "current", "measurement"),
            ("energy_kwh", "Energy", "kWh", "energy", "total_increasing"),
            ("temperature_c", "Temperature", "°C", "temperature", "measurement"),
        ):
            messages[f"homeassistant/sensor/{base}_{key}/config"] = {
                "name": f"Outlet {channel} {label}", "unique_id": base + "_" + key,
                "state_topic": root + f"/outlet/{channel}/{key}",
                "unit_of_measurement": unit, "device_class": devclass,
                "state_class": stateclass, "device": device, **online,
            }
    for key, label, unit, devclass in (
        ("voltage_v", "Voltage", "V", "voltage"),
        ("total_current_a", "Total current", "A", "current"),
        ("wifi_rssi_dbm", "Wi-Fi RSSI", "dBm", "signal_strength"),
    ):
        messages[f"homeassistant/sensor/voltra_{mac.lower()}_{key}/config"] = {
            "name": label, "unique_id": f"voltra_{mac.lower()}_{key}",
            "state_topic": root + "/" + key,
            "unit_of_measurement": unit, "device_class": devclass,
            "state_class": "measurement", "device": device, **online,
        }
    return messages


def matter_messages(strip: dict) -> dict[str, dict]:
    """Matterbridge-mqtt retained config/state/subscription; OnOffPlugInUnit."""
    mac = str(strip["mac"]).upper()
    if not MAC_RE.fullmatch(mac):
        raise ValueError("invalid strip MAC")
    name = str(strip.get("name") or "Voltra " + mac[-4:])
    channels = {int(o.get("channel") or 0): o for o in strip.get("outlets") or []}
    messages = {}
    for channel in range(1, 5):
        ident = f"voltra_{mac.lower()}_outlet_{channel}"
        root = f"matterbridge/{ident}"
        messages[root + "/config/root"] = {
            "deviceTypes": ["OnOffPlugInUnit"],
            "clusters": {"BridgedDeviceBasicInformation": {
                "nodeLabel": (name + f" Outlet {channel}")[:32],
                "serialNumber": f"{mac}-{channel}"[:32],
            }},
        }
        messages[root + "/state/root"] = {"OnOff": {"onOff": bool(channels.get(channel, {}).get("relay", False))}}
        messages[root + "/subscribe/root"] = {"OnOff": ["onOff"]}
    return messages


class MQTTBridge:
    def __init__(self, *, host: str, port: int = 1883, username: str = "",
                 password: str = "", snapshot_provider: Callable[[], list[dict]],
                 command_executor: Callable[[str, int, bool], dict],
                 matter_enabled: bool = False, audit=None):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.snapshot_provider = snapshot_provider
        self.command_executor = command_executor
        self.matter_enabled = matter_enabled
        self.audit = audit
        self.client = None
        self._closed = threading.Event()
        self._connected = threading.Event()
        self._commands: queue.Queue[tuple[str, int, bool]] = queue.Queue(maxsize=64)
        self._last: dict[str, str] = {}
        self._worker: threading.Thread | None = None
        self._publisher: threading.Thread | None = None

    def _send(self, topic: str, value: object, *, force=False) -> None:
        if not self._connected.is_set() or self.client is None:
            return
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (dict, list)) else str(value)
        if not force and self._last.get(topic) == payload:
            return
        info = self.client.publish(topic, payload=payload, qos=1, retain=True)
        if info.rc == 0:
            self._last[topic] = payload

    def publish_snapshot(self, strips: list[dict]) -> None:
        for strip in strips:
            mac = str(strip.get("mac") or "").upper()
            if not MAC_RE.fullmatch(mac) or not strip.get("managed") or strip.get("state") not in {"active", "disabled"}:
                continue
            root = f"voltra/{mac}"
            for topic, payload in discovery_messages(strip).items():
                self._send(topic, payload)
            online = bool(strip.get("online") and strip.get("enabled") and strip.get("state") == "active")
            self._send(root + "/availability", "online" if online else "offline")
            if not online:
                continue
            for key in ("voltage_v", "total_current_a", "wifi_rssi_dbm"):
                if strip.get(key) is not None:
                    self._send(root + "/" + key, strip[key])
            for outlet in strip.get("outlets") or []:
                ch = outlet.get("channel")
                if ch not in (1, 2, 3, 4):
                    continue
                prefix = root + f"/outlet/{ch}/"
                self._send(prefix + "state", "ON" if outlet.get("relay") else "OFF")
                for key in ("power_w", "current_a", "energy_kwh", "temperature_c"):
                    if outlet.get(key) is not None:
                        self._send(prefix + key, outlet[key])
            if self.matter_enabled:
                for topic, value in matter_messages(strip).items():
                    self._send(topic, value)

    @staticmethod
    def parse_command(topic: str, payload: bytes, *, matter_enabled: bool = False) -> tuple[str, int, bool] | None:
        simple = COMMAND_TOPIC_RE.fullmatch(topic)
        if simple:
            if payload not in (b"ON", b"OFF"):
                return None
            return simple.group(1), int(simple.group(2)), payload == b"ON"
        if matter_enabled:
            match = MATTER_WRITE_RE.fullmatch(topic)
            if match:
                try:
                    obj = json.loads(payload)
                    value = obj["OnOff"]["onOff"]
                    if type(value) is not bool:
                        return None
                    return match.group(2).upper(), int(match.group(3)), value
                except (ValueError, KeyError, TypeError):
                    return None
        return None

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if int(reason_code) != 0:
            return
        self._last.clear()
        self._connected.set()
        client.subscribe("voltra/+/outlet/+/set", qos=1)
        if self.matter_enabled:
            client.subscribe("matterbridge/+/write/root", qos=1)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self._connected.clear()

    def _on_message(self, client, userdata, message):
        parsed = self.parse_command(message.topic, message.payload, matter_enabled=self.matter_enabled)
        if parsed is None:
            return
        try:
            self._commands.put_nowait(parsed)
        except queue.Full:
            if self.audit:
                self.audit.append("mqtt", "command_queue_full")

    def _execute_loop(self):
        while not self._closed.is_set():
            try:
                mac, channel, on = self._commands.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.command_executor(mac, channel, on)
            except Exception as exc:
                # Do not publish intended ON/OFF as the confirmed physical state.
                if self.audit:
                    self.audit.append("mqtt", "command_failed", mac=mac, outlet=channel, error=str(exc))
            finally:
                self._commands.task_done()
                try:
                    self.publish_snapshot(self.snapshot_provider())
                except Exception:
                    pass

    def _publish_loop(self):
        while not self._closed.is_set():
            if self._connected.is_set():
                try:
                    self.publish_snapshot(self.snapshot_provider())
                except Exception as exc:
                    if self.audit:
                        self.audit.append("mqtt", "publish_error", error=str(exc))
            self._closed.wait(5.0)

    def start(self):
        import paho.mqtt.client as mqtt  # optional dependency, installed in the Docker image
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="voltra-miqaat")
        if self.username:
            client.username_pw_set(self.username, self.password)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client = client
        client.connect_async(self.host, self.port, keepalive=30)
        client.loop_start()
        self._worker = threading.Thread(target=self._execute_loop, daemon=True)
        self._publisher = threading.Thread(target=self._publish_loop, daemon=True)
        self._worker.start()
        self._publisher.start()

    def stop(self):
        self._closed.set()
        if self.client is not None:
            self.client.disconnect()
            self.client.loop_stop()
        for thread in (self._worker, self._publisher):
            if thread is not None:
                thread.join(timeout=2)
