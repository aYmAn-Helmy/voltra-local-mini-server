from __future__ import annotations
import json
import unittest
from unittest.mock import Mock
from voltra_local.alerts import AlertMonitor, inspect_snapshot
from voltra_local.mqtt_bridge import MQTTBridge
from voltra_local.protocol import BootInfo, OutletInfo
from voltra_local.tcp_server import DeviceSession
from types import SimpleNamespace


def device():
    return {"mac": "D8AA59D28888", "online": True, "voltage_v": 220.0,
            "total_current_a": 0.85, "outlets": [
                {"channel": 1, "relay": True, "power_w": 185, "current_a": 0.85,
                 "temperature_c": 31, "overload_protection": False, "overheat_protection": False}
            ]}


class HighPriorityTests(unittest.TestCase):
    def test_current_reports_derive_per_outlet_and_sum(self):
        server = SimpleNamespace(device_metrics=lambda mac: {})
        session = DeviceSession(server, object(), ("127.0.0.1", 111))
        session.boot = BootInfo("lgutap", "D8AA59D28888", "D8AA59D28888", "1.0.66")
        session._handle_frame("up:power_report:1:850")
        session._handle_frame("up:power_report:2:120")
        snap = session.snapshot()
        self.assertEqual(snap["total_current_a"], 0.970)
        self.assertEqual(session.current_a[1], 0.85)

    def test_alerts_are_non_actuating_and_deduplicated(self):
        item = device()
        item["total_current_a"] = 13.5
        item["outlets"][0]["temperature_c"] = 82
        item["outlets"][0]["power_w"] = 1700
        events = Mock()
        audit = Mock()
        monitor = AlertMonitor(lambda: [item], events, audit, interval=5)
        result = monitor.scan()
        self.assertEqual({x["code"] for x in result},
                         {"high_power", "high_current", "high_temperature"})
        monitor.scan()
        self.assertEqual(events.publish.call_count, 3)
        self.assertEqual(audit.append.call_count, 3)
        item["total_current_a"] = 0.5
        item["outlets"][0]["power_w"] = 100
        item["outlets"][0]["temperature_c"] = 30
        self.assertEqual(monitor.scan(), [])
        monitor.scan()
        self.assertEqual(events.publish.call_count, 3)

    def test_mqtt_discovery_and_state_for_four_outlets(self):
        bridge = MQTTBridge("localhost", 1883, lambda: [device()], Mock())
        sink = Mock()
        bridge._client = sink
        bridge._connected = True
        bridge.publish_snapshot()
        calls = sink.publish.call_args_list
        self.assertEqual(sum("/config" in c.args[0] for c in calls), 23)
        self.assertIn("voltra/D8AA59D28888/outlet/1/state", [c.args[0] for c in calls])
        self.assertIn("voltra/D8AA59D28888/sensor/current", [c.args[0] for c in calls])
        self.assertIn("0.85", [c.args[1] for c in calls])
        bridge.publish_snapshot()
        self.assertEqual(sum("/config" in c.args[0] for c in sink.publish.call_args_list), 23)


if __name__ == "__main__":
    unittest.main()
