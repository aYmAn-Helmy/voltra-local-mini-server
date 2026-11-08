"""Native LAN HTTP transport for standalone MTTL-W01 devices.

No arbitrary URL proxies: only explicitly paired RFC1918 IPv4 device addresses,
fixed firmware paths, bounded JSON bodies, and MAC identity checks.
"""
from __future__ import annotations

from datetime import datetime, timezone
import http.client
import ipaddress
import json
import threading
import time
from urllib.parse import urlencode

from .standalone_codec import configuration_revision, decode_schedule, merge_patch, pack_configuration

NETWORKS = tuple(ipaddress.ip_network(x) for x in
                 ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def validate_ip(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("standalone device IP must be text")
    try:
        address = ipaddress.IPv4Address(raw.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError("enter an IPv4 address, not a URL or hostname") from exc
    if not any(address in network for network in NETWORKS):
        raise ValueError("standalone devices must be in a private LAN")
    return str(address)


def clean_mac(value: str) -> str:
    mac = str(value).replace(":", "").replace("-", "").upper()
    if len(mac) != 12 or any(x not in "0123456789ABCDEF" for x in mac):
        raise ValueError("invalid device MAC")
    return mac


class FirmwareHTTPError(OSError):
    pass


def _request(ip: str, path: str, method: str = "GET", body: bytes | None = None,
             extra_headers: dict | None = None, timeout: float = 2.5) -> dict:
    # Never follow redirects, resolve hostnames, send arbitrary paths or forward
    # user-supplied headers/credentials to LAN devices.
    ip = validate_ip(ip)
    allowed = {"/api/status", "/api/device", "/api/version", "/api/config",
               "/api/control", "/api/scan", "/api/wifi", "/api/energy",
               "/api/memory", "/api/firmware/status", "/api/firmware/upload"}
    if path not in allowed or method not in ("GET", "POST"):
        raise ValueError("firmware endpoint not allowed")
    if body is not None and len(body) > 450000:
        raise ValueError("request too large")
    headers = {"Accept": "application/json", "Host": ip, "Connection": "close"}
    if method == "POST":
        headers["Origin"] = f"http://{ip}"
        headers["Content-Type"] = "application/octet-stream"
    if extra_headers:
        headers.update(extra_headers)
    connection = http.client.HTTPConnection(ip, 80, timeout=timeout)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status not in (200, 202):
            raise FirmwareHTTPError(f"firmware returned HTTP {response.status} for {path}")
        payload = response.read(8193)
        if len(payload) > 8192:
            raise FirmwareHTTPError("unexpectedly large firmware reply")
        result = json.loads(payload.decode("utf-8"))
        if not isinstance(result, dict):
            raise FirmwareHTTPError("invalid firmware JSON")
        return result
    except (TimeoutError, ConnectionError, OSError, http.client.HTTPException) as exc:
        if isinstance(exc, FirmwareHTTPError):
            raise
        raise FirmwareHTTPError(f"device HTTP unavailable at {ip}") from exc
    finally:
        connection.close()


def _scale(data, key, divisor=1):
    value = data.get(key)
    if type(value) is not int:
        return None
    return round(value / divisor, 4)


class HTTPStandaloneSession:
    def __init__(self, manager, mac):
        self.manager, self.mac = manager, clean_mac(mac)

    def snapshot(self):
        result = self.manager.snapshot(self.mac)
        if not result or not result["online"]:
            raise KeyError(f"standalone {self.mac} is offline")
        return result

    def query_info(self):
        return self.manager.poll_one(self.mac)

    def set_outlet(self, channel, on):
        return self.manager.control(self.mac, channel - 1, on)

    def set_all(self, on):
        return self.manager.control(self.mac, 4, on)

    def set_timer(self, channel, minutes):
        details = self.manager.details(self.mac)
        timers = list(details["config"]["timer_minutes"])
        if type(channel) is not int or not 1 <= channel <= 4 or type(minutes) is not int or not 0 <= minutes <= 1440:
            raise ValueError("invalid timer")
        timers[channel - 1] = minutes
        self.manager.patch(self.mac, {"timer_minutes": timers,
                                       "revision": details["config"]["revision"]})
        self.manager.poll_one(self.mac)
        return self.snapshot()


class HTTPStandalone:
    def __init__(self, store, event_bus=None, audit=None, http=None, poll_interval: float = 2.0):
        self.store, self.event_bus, self.audit = store, event_bus, audit
        self.http = http or _request
        self.poll_interval = max(1.0, float(poll_interval))
        self._lock = threading.RLock()
        self._cache = {}
        self._locks = {}
        self._stop = threading.Event()
        self._thread = None

    def _paired(self):
        return {mac: meta["last_ip"] for mac, meta in self.store.strips().items()
                if meta.get("device_type") == "standalone_http" and meta.get("last_ip")}

    def _target(self, mac):
        mac = clean_mac(mac)
        meta = self.store.strip(mac)
        if not meta or meta.get("device_type") != "standalone_http":
            raise KeyError("device is not paired for native HTTP control")
        return validate_ip(meta.get("last_ip") or "")

    def _device_lock(self, mac):
        mac = clean_mac(mac)
        with self._lock:
            return self._locks.setdefault(mac, threading.RLock())

    def pair(self, ip):
        ip = validate_ip(ip)
        status = self.http(ip, "/api/status")
        version = self.http(ip, "/api/version")
        mac = clean_mac(status.get("mac", ""))
        if not str(version.get("version", "")).startswith("2.1."):
            raise ValueError("this IP is not a supported standalone firmware 2.1.x device")
        if status.get("state") not in (2, 5):
            raise ValueError("standalone firmware must be ready and joined to Wi-Fi")
        # The device's identity is read from the actual physical device.
        self.store.record_strip({
            "mac": mac, "remote_address": f"{ip}:80",
            "model": "MTTL-W01", "firmware_version": str(version["version"]),
            "device_type": "standalone_http"
        })
        self.poll_one(mac)
        if self.audit:
            self.audit.append("standalone", "device_paired", mac=mac, ip=ip)
        return {"mac": mac, "ip": ip, "firmware_version": version["version"], "paired": True}

    def _check(self, ip, mac):
        status = self.http(ip, "/api/status")
        if clean_mac(status.get("mac", "")) != clean_mac(mac):
            raise FirmwareHTTPError("device MAC at saved IP has changed; refusing commands")
        return status

    def poll_one(self, mac):
        mac = clean_mac(mac)
        with self._device_lock(mac):
            return self._poll_locked(mac)

    def _poll_locked(self, mac):
        ip = self._target(mac)
        try:
            status = self._check(ip, mac)
            data = self.http(ip, "/api/device")
            channels = data.get("channels")
            if not isinstance(channels, list) or len(channels) != 4:
                raise FirmwareHTTPError("device snapshot missing channels")
            if status.get("state") != 5:
                raise FirmwareHTTPError("device is not in connected state")
            config = None
            with self._lock:
                prior = self._cache.get(mac)
                if prior:
                    config = prior.get("config")
            outlets = []
            for i, channel in enumerate(channels):
                if not isinstance(channel, dict):
                    raise FirmwareHTTPError("invalid firmware channel")
                outlet = {
                    "channel": i + 1, "name": channel.get("name"),
                    "relay": channel.get("on") if type(channel.get("on")) is bool else None,
                    "power_w": _scale(channel, "power_mw", 1000),
                    "energy_kwh": _scale(channel, "meter_wh", 1000),
                    "current_a": _scale(channel, "current_ma", 1000),
                    "temperature_c": _scale(channel, "temp_dc", 10),
                    "button_locked": channel.get("locked") is True,
                }
                if config:
                    timers = config.get("timer_minutes") or [0, 0, 0, 0]
                    outlet["timer_minutes"] = timers[i]
                outlets.append(outlet)
            snapshot = {
                "mac": mac, "online": True, "device_type": "standalone_http",
                "model": "MTTL-W01", "firmware_version": "Standalone 2.1.x",
                "remote_address": f"{ip}:80",
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "voltage_v": _scale(data, "voltage_dv", 10),
                "wifi_rssi_dbm": status.get("rssi"),
                "total_power_w": _scale(data, "power_mw", 1000),
                "total_energy_kwh": _scale(data, "meter_wh", 1000),
                "total_current_a": _scale(data, "current_ma", 1000),
                "outlets": outlets, "metrics": {},
                "hardware_ready": data.get("hardware_ready") is True,
                "protection": data.get("protection") or {},
            }
            with self._lock:
                previous = self._cache.get(mac, {}).get("snapshot")
                self._cache[mac] = {"snapshot": snapshot, "device": data, "status": status,
                                    "config": config, "at": time.monotonic()}
            if self.event_bus and (not previous or previous.get("outlets") != outlets):
                self.event_bus.publish("device_state", mac=mac)
            if self.audit and previous:
                before = tuple(x.get("relay") for x in previous.get("outlets", []))
                after = tuple(x.get("relay") for x in outlets)
                if before != after:
                    self.audit.append("standalone", "relay_state_changed", mac=mac,
                                      before=before, after=after)
            return snapshot
        except (FirmwareHTTPError, ValueError, KeyError):
            with self._lock:
                old = self._cache.get(mac, {})
                if old:
                    self._cache[mac] = {**old, "snapshot": {**old["snapshot"], "online": False}}
            raise

    def snapshot(self, mac):
        mac = clean_mac(mac)
        with self._lock:
            item = self._cache.get(mac)
            if not item:
                return None
            state = dict(item["snapshot"])
            state["online"] = state["online"] and time.monotonic() - item["at"] < 12
            return state

    def has_device(self, mac):
        return clean_mac(mac) in self._paired()

    def list_devices(self):
        return [s for mac in self._paired() if (s := self.snapshot(mac)) and s["online"]]

    def get(self, mac):
        if not self.snapshot(mac) or not self.snapshot(mac)["online"]:
            self.poll_one(mac)
        return HTTPStandaloneSession(self, mac)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="standalone-http", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            for mac in self._paired():
                if self._stop.is_set():
                    return
                try:
                    self.poll_one(mac)
                except (FirmwareHTTPError, ValueError, KeyError):
                    pass
            self._stop.wait(self.poll_interval)

    def _safe_request(self, mac, path, method="GET", body=None, extra_headers=None, timeout=2.5):
        ip = self._target(mac)
        self._check(ip, mac)  # Avoid talking to a different host after DHCP changes.
        return self.http(ip, path, method, body, extra_headers, timeout)

    def control(self, mac, channel, on):
        self.store.require_strip_controllable(mac)
        if type(channel) is not int or not 0 <= channel <= 4 or type(on) is not bool:
            raise ValueError("invalid native relay command")
        ip = self._target(mac)
        with self._device_lock(mac):
            self._check(ip, mac)
            # Native firmware accepts channel 0..3, 4 for ALL, with raw 2-byte POST.
            accepted = self.http(ip, "/api/control", "POST", bytes([channel, int(on)]))
            if accepted.get("accepted") is not True:
                raise FirmwareHTTPError("native relay command was not accepted")
            deadline = time.monotonic() + 4.0
            while time.monotonic() < deadline:
                try:
                    snapshot = self.poll_one(mac)
                    channels = snapshot["outlets"] if channel == 4 else [snapshot["outlets"][channel]]
                    if all(item.get("relay") is on for item in channels):
                        if self.audit:
                            self.audit.append("standalone", "relay_confirmed",
                                              mac=clean_mac(mac), channel=channel, on=on)
                        return snapshot
                except (FirmwareHTTPError, KeyError):
                    pass
                time.sleep(.15)
            raise TimeoutError("native relay command accepted, but not confirmed; refresh state before retry")

    def details(self, mac):
        ip = self._target(mac)
        status = self._check(ip, mac)
        device = self.http(ip, "/api/device")
        config = self.http(ip, "/api/config")
        if not isinstance(config.get("channels"), list) or len(config["channels"]) != 4:
            raise FirmwareHTTPError("device config is incomplete")
        with self._lock:
            if mac in self._cache:
                self._cache[mac]["config"] = config
        result = {
            "device": device, "status": status,
            "config": {**config, "schedule": decode_schedule(config["schedule_hex"]),
                       "revision": configuration_revision(config)},
        }
        for endpoint, label in (("/api/energy", "energy"), ("/api/memory", "memory"),
                                ("/api/firmware/status", "firmware")):
            try:
                result[label] = self.http(ip, endpoint)
            except (FirmwareHTTPError, ValueError):
                result[label] = None
        return result

    def live(self, mac):
        self.poll_one(mac)
        with self._lock:
            current = self._cache.get(clean_mac(mac))
            if not current:
                raise KeyError("standalone device has no live data")
            return {"device": dict(current["device"]), "status": dict(current["status"]),
                    "snapshot": dict(current["snapshot"])}

    def scan(self, mac, trigger=False):
        ip = self._target(mac)
        self._check(ip, mac)
        if trigger:
            return self.http(ip, "/api/scan", "POST", b"")
        return self.http(ip, "/api/scan")

    def _new_timers(self, mac, channel, minutes):
        if type(channel) is not int or not 1 <= channel <= 4:
            raise ValueError("outlet must be 1..4")
        if type(minutes) is not int or not 0 <= minutes <= 1440:
            raise ValueError("timer must be 0..1440 minutes")
        config = self.details(mac)["config"]
        timers = list(config["timer_minutes"])
        timers[channel - 1] = minutes
        return timers

    def patch(self, mac, patch):
        mac = clean_mac(mac)
        self.store.require_strip_controllable(mac)
        ip = self._target(mac)
        with self._device_lock(mac):
            self._check(ip, mac)
            before = self.http(ip, "/api/config")
            expected_revision = patch.get("revision")
            if not isinstance(expected_revision, str) or expected_revision != configuration_revision(before):
                raise ValueError("device settings changed; refresh before saving")
            cleaned = {key: value for key, value in patch.items() if key != "revision"}
            candidate, password, keep_password = merge_patch(before, cleaned)
            body = pack_configuration(candidate, password)
            wanted = {key: candidate[key] for key in candidate if key != "revision"}
            if configuration_revision(candidate) == configuration_revision(before) and keep_password:
                return self.details(mac)["config"]
            headers = {"X-MTTL-Keep-Password": "1" if keep_password else "0"}
            # Only send once: a lost 202 does not mean the flash operation failed.
            write_uncertain = False
            try:
                response = self.http(ip, "/api/config", "POST", body, headers, 4.0)
                if response.get("accepted") is not True:
                    raise FirmwareHTTPError("firmware rejected settings update")
            except FirmwareHTTPError:
                write_uncertain = True
            deadline = time.monotonic() + 4.5
            while time.monotonic() < deadline:
                try:
                    saved = self.http(ip, "/api/config")
                    equal = all(saved.get(k) == v for k, v in wanted.items()
                                if k not in ("persistent", "wifi_password_set", "mqtt_password_set"))
                    if equal and saved.get("persistent") is True:
                        with self._lock:
                            if mac in self._cache:
                                self._cache[mac]["config"] = saved
                        if self.audit:
                            self.audit.append("standalone", "config_saved", mac=mac, keys=list(cleaned))
                        return {**saved, "schedule": decode_schedule(saved["schedule_hex"]),
                                "revision": configuration_revision(saved)}
                except (FirmwareHTTPError, KeyError, ValueError):
                    pass
                time.sleep(.25)
            raise TimeoutError("device flash save is unconfirmed; refresh before retrying" +
                               (" (network reply lost)" if write_uncertain else ""))

    def wifi(self, mac, ssid, password):
        self.store.require_strip_controllable(mac)
        if not isinstance(ssid, str) or not 1 <= len(ssid.encode("utf-8")) <= 32:
            raise ValueError("Wi-Fi SSID must contain 1..32 bytes")
        if not isinstance(password, str) or (password and not 8 <= len(password) <= 64):
            raise ValueError("Wi-Fi password must be empty or 8..64 characters")
        with self._device_lock(mac):
            body = urlencode({"ssid": ssid, "password": password}).encode("ascii")
            result = self._safe_request(mac, "/api/wifi", "POST", body, 
                                        {"Content-Type": "application/x-www-form-urlencoded"}, 4.0)
            if self.audit:
                self.audit.append("standalone", "wifi_reconfigure", mac=clean_mac(mac))
            return result

    def firmware_status(self, mac):
        ip = self._target(mac)
        self._check(ip, mac)
        return self.http(ip, "/api/firmware/status")

    def ota(self, mac, data: bytes):
        """Optional firmware upload, never retried after the single POST."""
        self.store.require_strip_controllable(mac)
        if not isinstance(data, bytes) or not 44 <= len(data) <= 0x6A014:
            raise ValueError("expected bounded standalone .fwr binary")
        with self._device_lock(mac):
            status = self.firmware_status(mac)
            if status.get("ota_ready") is not True:
                raise ValueError("firmware does not allow OTA uploads")
            ip = self._target(mac)
            response = self.http(ip, "/api/firmware/upload", "POST", data,
                                 {"Content-Type": "application/x-mttl-fwr"}, 155.0)
            if self.audit:
                self.audit.append("standalone", "firmware_upload", mac=clean_mac(mac),
                                  size_bytes=len(data), activated=response.get("activated") is True)
            return response
