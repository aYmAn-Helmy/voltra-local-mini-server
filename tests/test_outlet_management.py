import tempfile
import unittest
from pathlib import Path

from voltra_local.audit import AuditLog
from voltra_local.automation import AutomationEngine
from voltra_local.outlet_control import OutletManager
from voltra_local.store import ConfigStore

MAC = "D8AA59D28888"


class DummySession:
    def __init__(self):
        self.relays = {i: False for i in range(1, 5)}
        self.calls = []

    def set_outlet(self, channel, on):
        self.calls.append((channel, on))
        self.relays[channel] = on
        return {"mac": MAC, "metrics": {"last_command_confirmed": True},
                "outlets": [{"channel": n, "relay": value}
                            for n, value in self.relays.items()]}

    def snapshot(self):
        return {"mac": MAC, "outlets": [{"channel": n, "relay": value}
                                       for n, value in self.relays.items()]}


class DummyMTTL:
    def __init__(self):
        self.session = DummySession()

    def get(self, mac):
        return self.session


class OutletManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.store = ConfigStore(base / "voltra.json")
        self.store.record_strip({"mac": MAC, "remote_address": "192.168.1.10:10086"})
        self.store.adopt_strip(MAC, "Living room")
        self.mttl = DummyMTTL()
        self.audit = AuditLog(base / "audit.jsonl")
        self.manager = OutletManager(self.store, self.mttl, audit=self.audit)
        self.automation = AutomationEngine(
            base / "automation.json", lambda: [],
            lambda mac, channel, on, source: self.manager.command(
                mac, channel, on, source=source),
            audit=self.audit)
        self.manager.bind_automation(self.automation)

    def test_arabic_names_survive_reload_and_backup(self):
        value = self.manager.preferences(MAC, 1, {"name": "بلايستيشن ٥",
                                                  "icon": "gamepad", "locked": False})
        self.assertEqual(value["name"], "بلايستيشن ٥")
        self.assertEqual(ConfigStore(self.store.path).outlet_preferences(MAC, 1)["name"], "بلايستيشن ٥")
        self.assertEqual(self.store.export_data()["strips"][MAC]["outlet_preferences"]["1"]["name"], "بلايستيشن ٥")

    def test_protection_and_lock_are_enforced_at_server(self):
        self.manager.preferences(MAC, 1, {"protected": True})
        self.manager.command(MAC, 1, True)
        with self.assertRaises(PermissionError):
            self.manager.command(MAC, 1, False)
        with self.assertRaises(PermissionError):
            self.manager.command(MAC, 1, False, source="scene")
        self.manager.command(MAC, 1, False, confirmed=True)
        self.manager.preferences(MAC, 1, {"locked": True})
        with self.assertRaises(PermissionError):
            self.manager.command(MAC, 1, True)

    def test_auto_off_countdown_and_cancel(self):
        self.manager.preferences(MAC, 2, {"auto_off_minutes": 5})
        self.manager.command(MAC, 2, True)
        auto = [x for x in self.automation.snapshot()["schedules"].values()
                if x.get("managed_key", "").endswith("auto_off")]
        self.assertEqual(len(auto), 1)
        self.assertFalse(auto[0]["on"])
        self.manager.command(MAC, 2, False)
        self.assertFalse([x for x in self.automation.snapshot()["schedules"].values()
                          if x.get("managed_key", "").endswith("auto_off")])

    def test_low_power_and_high_power_rules_reconcile(self):
        prefs = {"low_power_enabled": True, "low_power_threshold_w": 5,
                 "low_power_duration_s": 120, "alert_above_w": 1000}
        self.manager.preferences(MAC, 3, prefs)
        rules = list(self.automation.snapshot()["rules"].values())
        self.assertEqual({x["condition"] for x in rules}, {"low_power", "high_power"})
        self.manager.preferences(MAC, 3, {"low_power_enabled": False, "alert_above_w": 0})
        self.assertEqual(self.automation.snapshot()["rules"], {})

    def test_activity_filters_by_outlet_and_remembers_relay(self):
        self.manager.command(MAC, 1, True)
        self.manager.command(MAC, 2, True)
        items = self.manager.activity(MAC, 1)
        self.assertTrue(items)
        self.assertTrue(all(x["details"]["outlet"] == 1 for x in items))
        self.assertTrue(self.store.outlet_preferences(MAC, 1)["last_relay"])

    def test_restore_is_opt_in_and_no_uncommanded_toggle_by_default(self):
        self.manager.command(MAC, 1, True)
        self.mttl.session.calls.clear()
        self.manager.on_device_ready(type("Ready", (), {"mac": MAC})())
        self.assertFalse(self.mttl.session.calls)
        self.manager.preferences(MAC, 1, {"restore_policy": "last"})
        self.mttl.session.relays[1] = False
        self.manager.on_device_ready(type("Ready", (), {"mac": MAC})())
        self.assertEqual(self.mttl.session.calls, [(1, True)])

    def test_invalid_fields_rejected(self):
        for values in ({"name": "a" * 81}, {"locked": 1}, {"restore_policy": "on"},
                       {"auto_off_minutes": -1}, {"icon": "remote-code"}):
            with self.assertRaises(ValueError):
                self.manager.preferences(MAC, 1, values)


if __name__ == "__main__":
    unittest.main()
