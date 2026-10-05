import tempfile
import unittest
from pathlib import Path

from voltra_local.automation import AutomationEngine
from voltra_local.store import ConfigStore
from voltra_local.telemetry import TelemetryStore


MAC = "D8AA59D28888"


class MobilePlatformTests(unittest.TestCase):
    def test_server_side_preferences_scenes_and_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp) / "voltra.json")
            store.record_strip({"mac": MAC, "remote_address": "192.168.1.20:10086"})
            store.adopt_strip(MAC, "Room Strip")

            prefs = store.set_strip_preferences(MAC, room="VIP", favorite=True, sort_order=3)
            self.assertEqual(prefs["room"], "VIP")
            self.assertTrue(prefs["favorite"])
            self.assertEqual(prefs["sort_order"], 3)

            scene = store.upsert_scene(
                "night",
                "Night",
                [{"mac": MAC, "outlet": 1, "on": False}],
            )
            self.assertEqual(scene["actions"][0]["outlet"], 1)
            self.assertEqual(store.scenes()[0]["name"], "Night")

            settings = store.update_settings({
                "energy_price_per_kwh": 2.25,
                "currency": "EGP",
                "weak_wifi_dbm": -78,
            })
            self.assertEqual(settings["energy_price_per_kwh"], 2.25)
            self.assertEqual(settings["weak_wifi_dbm"], -78)

            backup = store.export_data()
            restored = ConfigStore(Path(tmp) / "restored.json")
            restored.import_data(backup)
            self.assertEqual(restored.strip(MAC)["room"], "VIP")
            self.assertEqual(restored.scenes()[0]["id"], "night")
            self.assertEqual(restored.settings()["currency"], "EGP")

    def test_one_time_schedule_and_countdown(self):
        calls = []
        devices = [{"mac": MAC, "online": True}]

        def execute(mac, outlet, on, source):
            calls.append((mac, outlet, on, source))
            return {"ok": True}

        with tempfile.TemporaryDirectory() as tmp:
            engine = AutomationEngine(
                Path(tmp) / "automation.json",
                snapshot_provider=lambda: list(devices),
                command_executor=execute,
            )
            once = engine.create_schedule({
                "mac": MAC,
                "outlet": 2,
                "on": False,
                "run_at": "2000-01-01T00:00:00+00:00",
            })
            self.assertEqual(once["type"], "once")
            engine._run_schedules(devices)
            saved = engine.snapshot()["schedules"][once["id"]]
            self.assertFalse(saved["enabled"])
            self.assertIsNotNone(saved.get("last_run_at"))
            self.assertEqual(calls[0][:3], (MAC, 2, False))

            countdown = engine.create_countdown({
                "mac": MAC,
                "outlet": 1,
                "on": True,
                "delay_seconds": 60,
            })
            self.assertEqual(countdown["type"], "once")
            self.assertTrue(countdown["run_at"])

    def test_per_outlet_energy(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TelemetryStore(Path(tmp) / "telemetry.jsonl", sample_interval=60)
            store.record([{
                "mac": MAC,
                "outlets": [
                    {"channel": 1, "power_w": 20, "energy_kwh": 1.0, "relay": True},
                    {"channel": 2, "power_w": 10, "energy_kwh": 2.0, "relay": True},
                ],
            }])
            store.record([{
                "mac": MAC,
                "outlets": [
                    {"channel": 1, "power_w": 25, "energy_kwh": 1.2, "relay": True},
                    {"channel": 2, "power_w": 5, "energy_kwh": 2.1, "relay": False},
                ],
            }])

            summary = store.summary(MAC, 24, outlet=1)
            history = store.history(MAC, 24, 96, outlet=2)

            self.assertAlmostEqual(summary["energy_kwh"], 0.2, places=5)
            self.assertEqual(summary["max_power_w"], 25.0)
            self.assertEqual(history["points"][0]["power_w"], 10.0)
            self.assertEqual(history["points"][1]["power_w"], 5.0)


if __name__ == "__main__":
    unittest.main()
