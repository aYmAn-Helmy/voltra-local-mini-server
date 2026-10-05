import tempfile
import unittest
from pathlib import Path

from voltra_local.telemetry import TelemetryStore


class TelemetryHistoryTests(unittest.TestCase):
    def test_history_returns_power_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TelemetryStore(Path(tmp) / "telemetry.jsonl", sample_interval=60)
            store.record([
                {
                    "mac": "D8AA59D28888",
                    "voltage_v": 223.4,
                    "wifi_rssi_dbm": -48,
                    "outlets": [
                        {"channel": 1, "power_w": 20.0, "energy_kwh": 1.0, "relay": True},
                        {"channel": 2, "power_w": 10.0, "energy_kwh": 2.0, "relay": True},
                    ],
                }
            ])
            store.record([
                {
                    "mac": "D8AA59D28888",
                    "voltage_v": 224.1,
                    "wifi_rssi_dbm": -50,
                    "outlets": [
                        {"channel": 1, "power_w": 25.0, "energy_kwh": 1.1, "relay": True},
                        {"channel": 2, "power_w": 5.0, "energy_kwh": 2.1, "relay": False},
                    ],
                }
            ])

            result = store.history("d8aa59d28888", hours=24, limit=96)

            self.assertEqual(result["mac"], "D8AA59D28888")
            self.assertEqual(result["samples"], 2)
            self.assertEqual(len(result["points"]), 2)
            self.assertEqual(result["points"][0]["power_w"], 30.0)
            self.assertEqual(result["points"][1]["voltage_v"], 224.1)


if __name__ == "__main__":
    unittest.main()
