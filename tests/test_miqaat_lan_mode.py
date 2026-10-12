from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from voltra_local.http_api import VoltraHTTPServer
from voltra_local.security import RemoteAccessSecurity
from voltra_local.store import ConfigStore


class DummyMTTL:
    def list_devices(self):
        return []


class TokenlessMiqaatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = VoltraHTTPServer(
            ("127.0.0.1", 0),
            DummyMTTL(),
            ConfigStore(Path(self.tmp.name) / "voltra.json"),
            api_token="",
            cors_origin="",
            lan_only=True,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def get(self, path, headers=None):
        return urlopen(Request(self.base + path, headers=headers or {}), timeout=3)

    def test_dashboard_and_api_work_without_bearer_key(self):
        with self.get("/health") as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(json.load(response)["ok"])
        with self.get("/voltra/api/overview") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("strips", json.load(response))
            self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))

    def test_public_hostname_is_blocked(self):
        with self.assertRaises(HTTPError) as raised:
            self.get("/voltra/api/overview", {"Host": "public.example.com"})
        self.assertEqual(raised.exception.code, 403)

    def test_proxy_headers_are_blocked_even_from_local_peer(self):
        for key in ("X-Forwarded-For", "X-Forwarded-Proto", "Forwarded"):
            with self.subTest(header=key):
                with self.assertRaises(HTTPError) as raised:
                    self.get("/api/status", {key: "203.0.113.10"})
                self.assertEqual(raised.exception.code, 403)

    def test_cross_origin_browser_access_is_blocked(self):
        with self.assertRaises(HTTPError) as raised:
            self.get("/voltra/api/overview", {"Origin": "https://evil.example"})
        self.assertEqual(raised.exception.code, 403)

        with self.get("/voltra/api/overview", {"Origin": self.base}) as response:
            self.assertEqual(response.status, 200)

    def test_policy_accepts_only_private_addresses_and_hosts(self):
        self.assertTrue(RemoteAccessSecurity.is_local_peer("192.168.1.45"))
        self.assertTrue(RemoteAccessSecurity.is_local_peer("10.0.0.8"))
        self.assertFalse(RemoteAccessSecurity.is_local_peer("8.8.8.8"))
        self.assertTrue(RemoteAccessSecurity.is_local_host("192.168.1.45:8086"))
        self.assertTrue(RemoteAccessSecurity.is_local_host("localhost:8086"))
        self.assertFalse(RemoteAccessSecurity.is_local_host("voltra.example.com:8443"))
        self.assertFalse(RemoteAccessSecurity.same_origin_host("192.168.1.45:8086", "https://evil.example"))


if __name__ == "__main__":
    unittest.main()
