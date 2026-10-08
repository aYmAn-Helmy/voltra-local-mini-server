from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from voltra_local.http_api import VoltraHTTPServer
from voltra_local.store import ConfigStore


TOKEN = "test-token-" + ("x" * 40)


class DummyMTTL:
    def list_devices(self):
        return []


class HttpAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        store = ConfigStore(Path(self.tmp.name) / "voltra.json")
        self.server = VoltraHTTPServer(
            ("127.0.0.1", 0),
            DummyMTTL(),
            store,
            api_token=TOKEN,
            trusted_proxy="127.0.0.1/32",
            rate_limit_per_minute=2,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def _get(self, path, token=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return urlopen(Request(self.base + path, headers=headers), timeout=2)

    def test_health_remains_public(self):
        with self._get("/health") as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(json.load(response)["ok"])

    def test_protected_api_rejects_missing_and_wrong_token(self):
        for token in (None, "wrong"):
            with self.subTest(token=token):
                with self.assertRaises(HTTPError) as caught:
                    self._get("/api/status", token)
                self.assertEqual(caught.exception.code, 401)
                payload = json.loads(caught.exception.read().decode("utf-8"))
                self.assertEqual(payload["code"], "unauthorized")

        with self.assertRaises(HTTPError) as caught:
            self._get("/api/status", "wrong-again")
        self.assertEqual(caught.exception.code, 429)
        payload = json.loads(caught.exception.read().decode("utf-8"))
        self.assertEqual(payload["code"], "auth_rate_limited")

    def test_protected_api_accepts_correct_token(self):
        with self._get("/api/status", TOKEN) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["device_count"], 0)


if __name__ == "__main__":
    unittest.main()
