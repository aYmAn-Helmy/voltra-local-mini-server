import unittest

from voltra_local.health import health_from_snapshot


class HealthTests(unittest.TestCase):
    def test_healthy_device(self):
        result = health_from_snapshot({
            "online": True,
            "wifi_rssi_dbm": -50,
            "voltage_v": 225.0,
            "metrics": {"command_count": 10, "command_failures": 0, "disconnects": 0},
        })
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["status"], "healthy")

    def test_bad_radio_and_voltage_reduce_score(self):
        result = health_from_snapshot({
            "online": True,
            "wifi_rssi_dbm": -85,
            "voltage_v": 180.0,
            "metrics": {"command_count": 10, "command_failures": 4, "disconnects": 12},
        })
        self.assertLess(result["score"], 35)
        self.assertIn(result["status"], {"critical", "unstable"})
        self.assertIn("wifi_very_weak", result["reasons"])
        self.assertIn("voltage_critical", result["reasons"])

    def test_offline_is_zero(self):
        self.assertEqual(health_from_snapshot(None)["score"], 0)


if __name__ == "__main__":
    unittest.main()
