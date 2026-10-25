import tempfile
import unittest
from pathlib import Path

from voltra_local.store import ConfigStore

MAC = "D8AA59D28888"

class OutletManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "voltra.json"
        self.store = ConfigStore(self.path)
        self.store.record_strip({"mac": MAC, "remote_address": "192.168.1.12:10086"})
        self.store.adopt_strip(MAC, "مشترك الصالة")

    def tearDown(self):
        self.tmp.cleanup()

    def test_arabic_persists_after_reload(self):
        settings = self.store.set_outlet_preferences(MAC, 2,
            {"name": "تلفزيون الصالة", "icon": "tv", "notifications": True})
        self.assertEqual(settings["name"], "تلفزيون الصالة")
        reopened = ConfigStore(self.path)
        self.assertEqual(reopened.outlet_preferences(MAC)["2"]["name"], "تلفزيون الصالة")
        self.assertEqual(reopened.strip(MAC)["name"], "مشترك الصالة")

    def test_lock_prevents_on_and_off(self):
        self.store.set_outlet_preferences(MAC, 1, {"locked": True})
        with self.assertRaises(PermissionError):
            self.store.require_outlet_action(MAC, 1, True)
        with self.assertRaises(PermissionError):
            self.store.require_outlet_action(MAC, 1, False, confirmed=True)
        self.store.set_outlet_preferences(MAC, 1, {"locked": False})
        self.store.require_outlet_action(MAC, 1, True)

    def test_protected_off_requires_confirmation_and_blocks_schedules(self):
        self.store.set_outlet_preferences(MAC, 1, {"protected": True})
        self.store.require_outlet_action(MAC, 1, True)
        with self.assertRaises(PermissionError):
            self.store.require_outlet_action(MAC, 1, False)
        with self.assertRaises(PermissionError):
            self.store.require_outlet_action(MAC, 1, False, automated=True)
        self.store.require_outlet_action(MAC, 1, False, confirmed=True)

    def test_rejects_unknown_icon_invalid_bool_and_firmware_policy(self):
        for value in ({"icon": "not-real"}, {"locked": "false"},
                      {"restore_policy": "on"}, {"name": "x" * 81}):
            with self.assertRaises(ValueError):
                self.store.set_outlet_preferences(MAC, 1, value)

if __name__ == "__main__":
    unittest.main()
