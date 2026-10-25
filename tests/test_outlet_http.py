from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from voltra_local.http_api import VoltraHTTPServer
from voltra_local.outlet_control import OutletManager
from voltra_local.store import ConfigStore

MAC = "D8AA59D28888"


class Session:
    def __init__(self):
        self.relays = {x: False for x in range(1, 5)}

    def set_outlet(self, channel, on):
        self.relays[channel] = on
        return self.snapshot()

    def snapshot(self):
        return {"mac": MAC, "online": True, "model": "lgutap",
                "metrics": {"last_command_confirmed": True},
                "outlets": [
                    {"channel": k, "relay": v, "power_w": 4.0 if v else 0.0}
                    for k, v in self.relays.items()
                ]}


class MTTL:
    def __init__(self):
        self.session = Session()

    def get(self, mac):
        if mac != MAC:
            raise KeyError(mac)
        return self.session

    def list_devices(self):
        return [self.session.snapshot()]


class OutletHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ConfigStore(Path(self.tmp.name) / "voltra.json")
        self.store.record_strip({"mac": MAC, "remote_address": "127.0.0.1:10086"})
        self.store.adopt_strip(MAC, "مشترك غرفة الألعاب")
        self.mttl = MTTL()
        self.manager = OutletManager(self.store, self.mttl)
        self.server = VoltraHTTPServer(("127.0.0.1", 0), self.mttl, self.store,
                                        outlet_manager=self.manager, rate_limit_per_minute=60)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.addCleanup(self._shutdown)

    def _shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def call(self, method, path, data=None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        request = Request(self.base + path, data=body, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=4) as result:
                return result.status, json.load(result)
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_unicode_preferences_and_relay_continuity(self):
        path = f"/voltra/api/strips/{MAC}/outlets/1/preferences"
        status, item = self.call("PUT", path, {"name": "بلايستيشن ٥", "icon": "gamepad"})
        self.assertEqual(status, 200)
        self.assertEqual(item["name"], "بلايستيشن ٥")
        status, prefs = self.call("GET", path)
        self.assertEqual(status, 200)
        self.assertEqual(prefs["name"], "بلايستيشن ٥")
        status, overview = self.call("GET", "/voltra/api/overview")
        self.assertEqual(status, 200)
        self.assertEqual(overview["strips"][0]["outlets"][0]["preferences"]["name"], "بلايستيشن ٥")

    def test_server_returns_403_for_locked_and_unconfirmed_off(self):
        prefs = f"/voltra/api/strips/{MAC}/outlets/2/preferences"
        command = f"/voltra/api/strips/{MAC}/outlets/2/state"
        self.call("PUT", prefs, {"protected": True})
        self.assertEqual(self.call("POST", command, {"on": True})[0], 200)
        self.assertEqual(self.call("POST", command, {"on": False})[0], 403)
        self.assertEqual(self.call("POST", command, {"on": False, "confirm_protected": True})[0], 200)
        self.call("PUT", prefs, {"locked": True})
        self.assertEqual(self.call("POST", command, {"on": True})[0], 403)
        self.assertEqual(self.call("POST", f"/api/devices/{MAC}/outlets/2/state", {"on": True})[0], 403)

    def test_invalid_updates_are_rejected(self):
        path = f"/voltra/api/strips/{MAC}/outlets/3/preferences"
        status, _ = self.call("PUT", path, {"icon": "invalid"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
