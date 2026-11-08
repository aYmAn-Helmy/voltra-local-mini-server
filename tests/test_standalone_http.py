from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from voltra_local.standalone_codec import (
    configuration_revision, decode_schedule, encode_schedule,
    pack_configuration, merge_patch, validate_timer_conflict,
)
from voltra_local.standalone_http import HTTPStandalone, FirmwareHTTPError, validate_ip
from voltra_local.store import ConfigStore


MAC = "D8AA59D3071D"
IP = "192.168.1.88"
EMPTY = {"minute": 0, "mode": 0, "day": 0, "channel": 0, "on": 0}


def config():
    return {
        "device": "Test standalone", "channels": ["SW 1", "SW 2", "SW 3", "SW 4"],
        "language": 1, "broker": "192.168.1.50", "port": 1883,
        "user": "voltra_device", "topic": "mttl", "enabled": False,
        "persistent": True, "mqtt_password_set": True,
        "wifi_password_set": True, "button_lock": 0,
        "timer_minutes": [0, 0, 0, 0],
        "protection": {"enabled": 7, "temperature": 90, "current": 16000, "power": 3000},
        "schedule_hex": encode_schedule({"timezone": 120, "rules": [dict(EMPTY) for _ in range(8)]}).hex(),
    }


class FirmwareStub:
    def __init__(self):
        self.config = config()
        self.status = {"mac": "d8:aa:59:d3:07:1d", "state": 5, "rssi": -42,
                       "uptime_ms": 120000, "hardware_ready": True, "ssid_hex": ""}
        self.device = {"channels": [{"name": f"SW {i}", "on": False, "locked": False,
                                     "power_mw": 0, "meter_wh": 0, "current_ma": 0, "temp_dc": 250}
                                    for i in range(1, 5)],
                       "power_mw": 0, "meter_wh": 0, "voltage_dv": 2310,
                       "current_ma": 0, "hardware_ready": True,
                       "timer_running": 0, "timer_end": [0, 0, 0, 0],
                       "mqtt_state": 0}
        self.requests = []
        self.miss_write_reply = False

    def __call__(self, ip, path, method="GET", body=None, extra_headers=None, timeout=2.5):
        assert ip == IP
        self.requests.append((path, method, body, extra_headers))
        if method == "GET":
            mapping = {"/api/status": self.status, "/api/device": self.device,
                       "/api/version": {"version": "2.1.1"},
                       "/api/config": self.config,
                       "/api/scan": {"pending": False, "networks": []},
                       "/api/energy": {}, "/api/memory": {},
                       "/api/firmware/status": {"ota_ready": False}}
            if path not in mapping:
                raise FirmwareHTTPError("unknown")
            return json.loads(json.dumps(mapping[path]))
        if path == "/api/control":
            channel, state = body
            targets = range(4) if channel == 4 else [channel]
            for i in targets:
                self.device["channels"][i]["on"] = bool(state)
            return {"accepted": True}
        if path == "/api/config":
            self.config["schedule_hex"] = body[-59:-9].hex()
            self.config["button_lock"] = body[-9]
            self.config["timer_minutes"] = list(struct.unpack("<4H", body[-8:]))
            self.config["persistent"] = True
            if self.miss_write_reply:
                raise FirmwareHTTPError("reply lost")
            return {"accepted": True, "pending": True}
        if path == "/api/wifi":
            return {"accepted": True, "persistent": False}
        if path == "/api/scan":
            return {"accepted": True}
        raise FirmwareHTTPError("unexpected POST")


class FirmwareCodecTests(unittest.TestCase):
    def test_schedule_50_bytes_roundtrip(self):
        value = {"timezone": 180, "rules": [dict(EMPTY) for _ in range(8)]}
        value["rules"][0] = {"minute": 870, "mode": 130, "day": 31, "channel": 2, "on": 1}
        raw = encode_schedule(value)
        self.assertEqual(len(raw), 50)
        self.assertEqual(decode_schedule(raw.hex()), value)

    def test_schedule_validation_and_conflicts(self):
        schedule = {"timezone": 120, "rules": [dict(EMPTY) for _ in range(8)]}
        schedule["rules"][0] = {"minute": 360, "mode": 129, "day": 0, "channel": 4, "on": 1}
        with self.assertRaises(ValueError):
            validate_timer_conflict(schedule, [0, 30, 0, 0])
        with self.assertRaises(ValueError):
            encode_schedule({**schedule, "timezone": 127})
        with self.assertRaises(ValueError):
            encode_schedule({**schedule, "rules": schedule["rules"][:7]})

    def test_firmware_config_binary_format_v7(self):
        raw = pack_configuration(config())
        self.assertEqual(raw[:5], bytes([7, 1, 0, 91, 7]))
        self.assertEqual(len(raw) < 1024, True)
        self.assertEqual(raw[-59:-9], bytes.fromhex(config()["schedule_hex"]))
        self.assertEqual(list(struct.unpack("<4H", raw[-8:])), [0, 0, 0, 0])
        candidate, password, preserve = merge_patch(config(), {"timer_minutes": [0, 2, 0, 0]})
        self.assertEqual(candidate["timer_minutes"][1], 2)
        self.assertEqual(password, "")
        self.assertTrue(preserve)
        self.assertEqual(configuration_revision(config()), configuration_revision(dict(config())))

    def test_rejects_lan_ssrf_targets(self):
        for bad in ("127.0.0.1", "169.254.169.254", "8.8.8.8", "localhost",
                    "http://192.168.1.1", "::1", "0.0.0.0", "192.168.1.1:80"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_ip(bad)
        self.assertEqual(validate_ip(IP), IP)


class NativeFirmwareIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self.dir.name) / "voltra.json")
        self.device = FirmwareStub()
        self.native = HTTPStandalone(self.store, http=self.device)

    def tearDown(self):
        self.dir.cleanup()

    def pair(self):
        result = self.native.pair(IP)
        self.assertEqual(result["mac"], MAC)
        self.assertEqual(self.store.strip(MAC)["device_type"], "standalone_http")
        self.store.adopt_strip(MAC)

    def test_pair_and_fast_direct_switch_buttons(self):
        self.pair()
        snap = self.native.get(MAC).set_outlet(2, True)
        self.assertTrue(snap["outlets"][1]["relay"])
        self.assertEqual([r[2] for r in self.device.requests if r[0] == "/api/control"], [bytes([1, 1])])
        snap = self.native.get(MAC).set_all(False)
        self.assertFalse(any(item["relay"] for item in snap["outlets"]))
        self.assertEqual([r[2] for r in self.device.requests if r[0] == "/api/control"][-1], bytes([4, 0]))

    def test_schedule_saved_on_device_and_can_be_edited(self):
        self.pair()
        details = self.native.details(MAC)
        schedule = details["config"]["schedule"]
        schedule["rules"][0] = {"minute": 420, "mode": 129, "day": 0, "channel": 0, "on": 1}
        saved = self.native.patch(MAC, {"schedule": schedule, "revision": details["config"]["revision"]})
        self.assertEqual(saved["schedule"]["rules"][0]["minute"], 420)
        again = self.native.details(MAC)
        self.assertEqual(again["config"]["schedule"]["rules"][0]["on"], 1)
        with self.assertRaises(ValueError):
            self.native.patch(MAC, {"schedule": schedule, "revision": "obsolete"})

    def test_dont_repeat_firmware_flash_if_reply_lost(self):
        self.pair()
        self.device.miss_write_reply = True
        details = self.native.details(MAC)
        result = self.native.patch(MAC, {"timer_minutes": [0, 0, 1, 0],
                                          "revision": details["config"]["revision"]})
        self.assertEqual(result["timer_minutes"][2], 1)
        posts = [r for r in self.device.requests if r[0] == "/api/config" and r[1] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][3].get("X-MTTL-Keep-Password"), "1")

    def test_cannot_write_unadopted_strip(self):
        self.native.pair(IP)
        details = self.native.details(MAC)
        with self.assertRaises(ValueError):
            self.native.patch(MAC, {"timer_minutes": [1, 0, 0, 0],
                                     "revision": details["config"]["revision"]})

    def test_mac_mismatch_blocks_replaced_ip(self):
        self.pair()
        self.device.status["mac"] = "aa:aa:aa:aa:aa:aa"
        with self.assertRaises(FirmwareHTTPError):
            self.native.control(MAC, 0, True)



class NativeHTTPAPITests(unittest.TestCase):
    def setUp(self):
        from threading import Thread
        from voltra_local.device_manager import DeviceManager
        from voltra_local.http_api import VoltraHTTPServer

        class EmptyTCP:
            def list_devices(self):
                return []

            def get(self, mac):
                raise KeyError(mac)

        self.tmp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self.tmp.name) / "state.json")
        self.mock = FirmwareStub()
        self.native = HTTPStandalone(self.store, http=self.mock)
        self.api_token = "tests-only-" + ("x" * 40)
        self.server = VoltraHTTPServer(
            ("127.0.0.1", 0), DeviceManager(EmptyTCP(), standalone=self.native),
            self.store, api_token=self.api_token, standalone=self.native,
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.root = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def call(self, path, payload=None, authenticated=True):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.api_token
        req = Request(self.root + path,
                      data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
                      headers=headers)
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_auth_adopt_and_flash_schedule_via_api(self):
        address = "/voltra/api/standalone"
        code, _ = self.call(address + "/pair", {"ip": IP}, authenticated=False)
        self.assertEqual(code, 401)
        code, created = self.call(address + "/pair", {"ip": IP})
        self.assertEqual(code, 201)
        self.assertEqual(created["mac"], MAC)
        code, _ = self.call(address + "/" + MAC + "/details")
        self.assertNotEqual(code, 200)  # pending cannot read config
        self.store.adopt_strip(MAC)
        code, details = self.call(address + "/" + MAC + "/details")
        self.assertEqual(code, 200)
        schedule = details["config"]["schedule"]
        schedule["rules"][0] = {"minute": 1140, "mode": 129, "day": 0, "channel": 0, "on": 0}
        code, saved = self.call(address + "/" + MAC + "/config", {
            "schedule": schedule, "revision": details["config"]["revision"]
        })
        self.assertEqual(code, 200, saved)
        self.assertEqual(saved["schedule"]["rules"][0]["minute"], 1140)
        from unittest.mock import Mock
        self.server.automation = Mock()
        code, _ = self.call("/voltra/api/schedules", {
            "mac": MAC, "outlet": 1, "on": True,
            "time": "19:00", "days": [0, 1, 2, 3, 4, 5, 6]
        })
        self.assertEqual(code, 400)

    def test_api_relay_uses_firmware_channel_index(self):
        address = "/voltra/api/standalone"
        self.call(address + "/pair", {"ip": IP})
        self.store.adopt_strip(MAC)
        code, snap = self.call(f"/voltra/api/strips/{MAC}/outlets/1/state", {"on": True})
        self.assertEqual(code, 200, snap)
        self.assertTrue(snap["outlets"][0]["relay"])
        self.assertEqual(
            [r[2] for r in self.mock.requests if r[0] == "/api/control"][-1],
            bytes([0, 1]),
        )
        code, snap = self.call(f"/voltra/api/strips/{MAC}/all/state", {"on": False})
        self.assertEqual(code, 200, snap)
        self.assertEqual(
            [r[2] for r in self.mock.requests if r[0] == "/api/control"][-1],
            bytes([4, 0]),
        )


if __name__ == "__main__":
    unittest.main()
