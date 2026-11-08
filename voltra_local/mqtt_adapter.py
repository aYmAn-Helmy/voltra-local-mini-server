"""MQTT integration for standalone MTTL-W01 firmware (v2.1.x)."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
import threading
import time


MAC = re.compile(r"^[0-9a-f]{12}$")
METRIC = re.compile(r"^(power|meter|current|temperature|timer|timer_remaining)([1-4])$")
FIELDS = {"power": "power_w", "meter": "energy_kwh", "current": "current_a",
          "temperature": "temperature_c", "timer": "timer_minutes",
          "timer_remaining": "timer_remaining_s"}


class StandaloneSession:
    def __init__(self, manager, mac):
        self.manager, self.mac = manager, mac

    def snapshot(self):
        snap = self.manager.snapshot(self.mac)
        if not snap or not snap["online"]:
            raise KeyError(f"standalone device {self.mac} is offline")
        return snap

    def query_info(self):
        return self.snapshot()

    def set_outlet(self, outlet, on):
        if type(outlet) is not int or outlet not in range(1, 5) or type(on) is not bool:
            raise ValueError("outlet must be 1..4 and on must be boolean")
        return self.manager.command(self.mac, f"sw{outlet}", "ON" if on else "OFF", on)

    def set_timer(self, outlet, minutes):
        if type(outlet) is not int or outlet not in range(1, 5) or type(minutes) is not int or not 0 <= minutes <= 1440:
            raise ValueError("invalid on-device timer")
        return self.manager.command(self.mac, f"timer{outlet}", str(minutes), minutes)


class StandaloneMQTT:
    def __init__(self, host, port=1883, username="", password="", prefix="voltra",
                 on_device_seen=None, event_bus=None, client=None):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", prefix):
            raise ValueError("invalid MQTT topic prefix")
        self.host, self.port, self.username, self.password, self.prefix = host, int(port), username, password, prefix
        self.on_device_seen, self.event_bus = on_device_seen, event_bus
        self._client = client
        self._cv = threading.Condition(threading.RLock())
        self._connected = False
        self._devices = {}

    def start(self):
        if self._client is None:
            import paho.mqtt.client as mqtt
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="voltra-server")
        if self.username:
            self._client.username_pw_set(self.username, self.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.connect_async(self.host, self.port, keepalive=45)
        self._client.loop_start()

    def stop(self):
        if self._client:
            self._client.disconnect()
            self._client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"[MQTT] connection rejected: {reason_code}")
            return
        with self._cv:
            self._connected = True
            self._cv.notify_all()
        client.subscribe(f"{self.prefix}/standalone/+/#", qos=1)
        print("[MQTT] connected")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        with self._cv:
            self._connected = False
            self._cv.notify_all()
        print(f"[MQTT] disconnected: {reason_code}")

    def _on_message(self, client, userdata, message):
        self.ingest(message.topic, message.payload)

    @staticmethod
    def _number(value):
        try:
            result = float(value)
        except (ValueError, TypeError):
            return None
        return result if math.isfinite(result) else None

    def ingest(self, topic, payload):
        parts = topic.split("/")
        if len(parts) != 4 or parts[:2] != [self.prefix, "standalone"] or not MAC.fullmatch(parts[2]) or len(payload) > 64:
            return
        try:
            value = payload.decode("ascii").strip()
        except UnicodeError:
            return
        metric = parts[3]
        if metric == "availability":
            if value not in ("online", "offline"):
                return
            result = value == "online"
        elif metric in ("all", "sw1", "sw2", "sw3", "sw4"):
            if value not in ("ON", "OFF"):
                return
            result = value == "ON"
        else:
            valid = metric in ("power", "meter", "voltage", "current") or bool(METRIC.fullmatch(metric))
            if not valid:
                return
            result = self._number(value)
            if result is None:
                return
            if metric.startswith("timer"):
                if int(result) != result or result < 0 or result > (86400 if metric.startswith("timer_remaining") else 1440):
                    return
                result = int(result)
        mac = parts[2].upper()
        created = False
        with self._cv:
            if mac not in self._devices:
                self._devices[mac] = {"available": False, "fields": {}, "last_seen_at": None,
                                      "last_mono": 0, "event_mono": 0}
                created = True
            item = self._devices[mac]
            old_value = item["available"] if metric == "availability" else item["fields"].get(metric)
            if metric == "availability":
                item["available"] = result
            else:
                item["fields"][metric] = result
            item["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            item["last_mono"] = time.monotonic()
            # Several strips stream telemetry frequently. Coalesce UI refreshes,
            # but always emit changed relay/availability reports.
            publish_event = (metric in ("availability", "all", "sw1", "sw2", "sw3", "sw4")
                             and old_value != result) or (item["last_mono"] - item["event_mono"] >= 3)
            if publish_event:
                item["event_mono"] = item["last_mono"]
            self._cv.notify_all()
        if created and self.on_device_seen:
            try:
                self.on_device_seen({"mac": mac, "model": "MTTL-W01", "device_type": "standalone_mqtt",
                                     "firmware_version": "Standalone 2.1.x"})
            except Exception as exc:
                print(f"[MQTT] registration failed: {exc}")
        if self.event_bus and publish_event:
            self.event_bus.publish("device_state", mac=mac)

    def snapshot(self, mac):
        mac = mac.replace(":", "").replace("-", "").upper()
        with self._cv:
            item = self._devices.get(mac)
            if item is None:
                return None
            fields = dict(item["fields"])
            online = self._connected and item["available"] and time.monotonic() - item["last_mono"] < 900
            seen = item["last_seen_at"]
        outlets = [
            {"channel": c, "relay": fields.get(f"sw{c}"),
             **{value: fields.get(f"{key}{c}") for key, value in FIELDS.items()}}
            for c in range(1, 5)
        ]
        return {"mac": mac, "online": online, "device_type": "standalone_mqtt",
                "model": "MTTL-W01", "firmware_version": "Standalone 2.1.x",
                "last_seen_at": seen, "voltage_v": fields.get("voltage"), "wifi_rssi_dbm": None,
                "total_power_w": fields.get("power"), "total_energy_kwh": fields.get("meter"),
                "total_current_a": fields.get("current"), "remote_address": "",
                "outlets": outlets, "metrics": {}}

    def list_devices(self):
        with self._cv:
            macs = list(self._devices)
        return [device for mac in macs if (device := self.snapshot(mac)) and device["online"]]

    def has_device(self, mac):
        with self._cv:
            return mac.replace(":", "").replace("-", "").upper() in self._devices

    def get(self, mac):
        session = StandaloneSession(self, mac.replace(":", "").replace("-", "").upper())
        session.snapshot()
        return session

    def command(self, mac, metric, value, expected):
        mac = mac.replace(":", "").replace("-", "").upper()
        with self._cv:
            item = self._devices.get(mac)
            if not self._connected or not item or not item["available"] or time.monotonic() - item["last_mono"] > 900:
                raise KeyError(f"device {mac} is offline")
            if item["fields"].get(metric) == expected:
                return self.snapshot(mac)
            suffix = metric[2:] if metric.startswith("sw") else metric
            address = f"{self.prefix}/standalone/{mac.lower()}/{suffix}/set"
            info = self._client.publish(address, value, qos=1, retain=False)
            if info.rc != 0:
                raise RuntimeError(f"MQTT publish failed: {info.rc}")
            deadline = time.monotonic() + 8
            while item["fields"].get(metric) != expected:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._connected or not item["available"]:
                    raise TimeoutError(f"no confirmed response from {mac}")
                self._cv.wait(remaining)
        return self.snapshot(mac)
