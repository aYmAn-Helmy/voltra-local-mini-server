from __future__ import annotations

import unittest
from unittest.mock import Mock

from voltra_local.device_manager import DeviceManager
from voltra_local.mqtt_adapter import StandaloneMQTT


class DummyTCP:
    def list_devices(self):
        return [{"mac": "AAAAAAAAAAAA", "outlets": [], "online": True}]

    def get(self, mac):
        if mac == "AAAAAAAAAAAA":
            return "legacy-tcp"
        raise KeyError(mac)


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.client = Mock()
        self.client.publish.return_value.rc = 0
        self.adapter = StandaloneMQTT("127.0.0.1", on_device_seen=self.seen.append, client=self.client)
        self.adapter._connected = True
        self.mac = "001122AABBCC"
        self.prefix = "voltra/standalone/001122aabbcc/"

    def report(self, metric, value):
        self.adapter.ingest(self.prefix + metric, value.encode("ascii"))

    def test_discovery_and_energy(self):
        self.report("availability", "online")
        self.report("sw1", "ON")
        self.report("power1", "12.500")
        self.report("meter1", "2.250")
        self.report("voltage", "230.1")
        self.report("timer_remaining1", "77")
        snap = self.adapter.snapshot(self.mac)
        self.assertTrue(snap["online"])
        self.assertEqual(snap["voltage_v"], 230.1)
        self.assertEqual(snap["outlets"][0]["power_w"], 12.5)
        self.assertEqual(snap["outlets"][0]["energy_kwh"], 2.25)
        self.assertEqual(snap["outlets"][0]["timer_remaining_s"], 77)
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(self.seen[0]["device_type"], "standalone_mqtt")

    def test_rejects_unexpected_topics_and_bad_numbers(self):
        self.adapter.ingest("other/standalone/001122aabbcc/sw1", b"ON")
        self.adapter.ingest(self.prefix + "sw1/set", b"ON")
        self.report("power1", "NaN")
        self.report("power1", "inf")
        self.report("sw1", "maybe")
        self.assertEqual(self.seen, [])

    def test_confirms_relay_change_with_no_retained_commands(self):
        self.report("availability", "online")
        self.report("sw2", "OFF")

        def publish(topic, payload, qos, retain):
            self.assertEqual(topic, self.prefix + "2/set")
            self.assertEqual(payload, "ON")
            self.assertEqual(qos, 1)
            self.assertFalse(retain)
            self.report("sw2", "ON")
            return Mock(rc=0)

        self.client.publish.side_effect = publish
        result = self.adapter.get(self.mac).set_outlet(2, True)
        self.assertTrue(result["outlets"][1]["relay"])

    def test_confirms_device_timer_change(self):
        self.report("availability", "online")
        self.report("timer3", "0")

        def publish(topic, payload, qos, retain):
            self.assertEqual(topic, self.prefix + "timer3/set")
            self.assertEqual(payload, "45")
            self.assertFalse(retain)
            self.report("timer3", "45")
            return Mock(rc=0)

        self.client.publish.side_effect = publish
        self.assertEqual(self.adapter.get(self.mac).set_timer(3, 45)["outlets"][2]["timer_minutes"], 45)
        with self.assertRaises(ValueError):
            self.adapter.get(self.mac).set_timer(3, 1441)

    def test_offline_device_not_listed(self):
        self.report("availability", "offline")
        self.assertEqual(self.adapter.list_devices(), [])
        with self.assertRaises(KeyError):
            self.adapter.get(self.mac)

    def test_sensor_messages_are_coalesced_for_ui(self):
        events = Mock()
        self.adapter.event_bus = events
        self.report("availability", "online")
        events.publish.reset_mock()
        for i in range(100):
            self.report("power1", str(10 + i))
        self.assertLessEqual(events.publish.call_count, 1)

    def test_both_transports_available(self):
        self.report("availability", "online")
        hub = DeviceManager(DummyTCP(), self.adapter)
        self.assertEqual(len(hub.list_devices()), 2)
        self.assertEqual(hub.get("AAAAAAAAAAAA"), "legacy-tcp")
        self.assertEqual(hub.get(self.mac).snapshot()["device_type"], "standalone_mqtt")


if __name__ == "__main__":
    unittest.main()
