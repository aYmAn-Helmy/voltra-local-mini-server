from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from types import SimpleNamespace
import unittest

from voltra_local.mqtt_bridge import MQTTBridge, discovery_messages, matter_messages
from voltra_local.protocol import parse_getinfo, power_current_request
from voltra_local.safety import SafetyMonitor, warning_candidates, is_fresh
from voltra_local.tcp_server import DeviceSession
from voltra_local.protocol import BootInfo, OutletInfo


MAC = "D8AA59D28888"


def sample_strip(current=1.2):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "mac": MAC, "name": "Office", "model": "lgutap",
        "managed": True, "enabled": True, "state": "active", "online": True,
        "last_info_at": now, "last_current_at": now, "last_diagnostics_at": now,
        "voltage_v": 220.0, "total_current_a": current, "wifi_rssi_dbm": -60,
        "outlets": [
            {"channel": i, "relay": i == 1, "power_w": 800.0 if i == 1 else 0,
             "current_a": current / 4, "energy_kwh": 0.8,
             "temperature_c": 31}
            for i in range(1, 5)
        ],
    }


class FakeMQTT:
    def __init__(self):
        self.sent = []
    def publish(self, topic, payload, qos=1, retain=False):
        self.sent.append((topic, payload, qos, retain))
        return SimpleNamespace(rc=0)


class MQTTIntegrationTests(unittest.TestCase):
    def test_discovery_exposes_real_ampere_and_switch_commands(self):
        messages = discovery_messages(sample_strip())
        channel = f"homeassistant/sensor/voltra_{MAC.lower()}_1_current_a/config"
        self.assertEqual(messages[channel]["device_class"], "current")
        self.assertEqual(messages[channel]["unit_of_measurement"], "A")
        switch = messages[f"homeassistant/switch/voltra_{MAC.lower()}_1/config"]
        self.assertEqual(switch["command_topic"], f"voltra/{MAC}/outlet/1/set")
        self.assertEqual(switch["state_topic"], f"voltra/{MAC}/outlet/1/state")

    def test_matter_plugin_uses_real_onoff_plug_endpoint(self):
        data = matter_messages(sample_strip())
        base = f"matterbridge/voltra_{MAC.lower()}_outlet_1"
        self.assertEqual(data[base + "/config/root"]["deviceTypes"], ["OnOffPlugInUnit"])
        self.assertEqual(data[base + "/state/root"]["OnOff"]["onOff"], True)
        self.assertEqual(data[base + "/subscribe/root"], {"OnOff": ["onOff"]})

    def test_commands_reject_unknown_payloads_and_channels(self):
        parse = MQTTBridge.parse_command
        self.assertEqual(parse(f"voltra/{MAC}/outlet/1/set", b"ON"), (MAC, 1, True))
        self.assertIsNone(parse(f"voltra/{MAC}/outlet/5/set", b"ON"))
        self.assertIsNone(parse(f"voltra/{MAC}/outlet/1/set", b"toggle"))
        self.assertIsNone(parse(f"voltra/{MAC}/outlet/1/set", b"on"))
        topic = f"matterbridge/voltra_{MAC.lower()}_outlet_2/write/root"
        self.assertEqual(parse(topic, b'{"OnOff":{"onOff":false}}', matter_enabled=True), (MAC, 2, False))
        self.assertIsNone(parse(topic, b'{"OnOff":{"onOff":1}}', matter_enabled=True))
        self.assertIsNone(parse(topic, b'{"OnOff":{"onOff":true}}', matter_enabled=False))

    def test_retained_publish_and_offline_availability(self):
        fake = FakeMQTT()
        bridge = MQTTBridge(host="127.0.0.1", snapshot_provider=lambda: [],
                            command_executor=lambda *args: {}, matter_enabled=True)
        bridge.client = fake
        bridge._connected.set()
        strip = sample_strip()
        bridge.publish_snapshot([strip])
        topics = {t: p for t, p, _, _ in fake.sent}
        self.assertIn(f"voltra/{MAC}/outlet/1/current_a", topics)
        self.assertIn(f"matterbridge/voltra_{MAC.lower()}_outlet_1/config/root", topics)
        self.assertTrue(all(qos == 1 and retain for _, _, qos, retain in fake.sent))
        old_count = len(fake.sent)
        bridge.publish_snapshot([strip])
        self.assertEqual(len(fake.sent), old_count)
        bridge.publish_snapshot([{**strip, "online": False}])
        self.assertIn((f"voltra/{MAC}/availability", "offline", 1, True), fake.sent)


class SafetyTests(unittest.TestCase):
    def test_freshness_rejects_stale_and_missing_timestamps(self):
        self.assertFalse(is_fresh(None))
        self.assertFalse(is_fresh((datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()))
        self.assertTrue(is_fresh(datetime.now(timezone.utc).isoformat()))

    def test_threshold_candidates_require_physical_freshness(self):
        strip = sample_strip(current=13.0)
        strip["outlets"][0]["temperature_c"] = 82
        thresholds = {"alert_max_total_current_a": 12.0, "alert_max_temperature_c": 75}
        warnings = warning_candidates(strip, thresholds)
        self.assertIn(("high_current", 0), warnings)
        self.assertIn(("high_temperature", 1), warnings)
        strip["last_current_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.assertNotIn(("high_current", 0), warning_candidates(strip, thresholds))

    def test_two_distinct_samples_raise_single_alert_and_do_not_shutdown_by_default(self):
        strip = sample_strip()
        strip["outlets"][0]["power_w"] = 3200
        commands = []
        events = []
        class Bus:
            def publish(self, event, **details):
                events.append(event)
        m = SafetyMonitor(snapshot_provider=lambda: [strip], settings_provider=lambda: {},
                          command_executor=lambda *args: commands.append(args), event_bus=Bus())
        m.evaluate([strip])
        self.assertFalse(m.active())
        m.evaluate([strip])
        self.assertFalse(m.active())  # same measurement sample
        strip2 = {**strip, "last_info_at": (datetime.now(timezone.utc) + timedelta(milliseconds=50)).isoformat()}
        m.evaluate([strip2])
        self.assertEqual(len(m.active()), 1)
        self.assertEqual(m.active()[0]["kind"], "high_power")
        self.assertEqual(commands, [])
        self.assertEqual(events.count("safety_alert_raised"), 1)
        strip2["outlets"][0]["power_w"] = 0
        m.evaluate([strip2])
        self.assertEqual(m.active(), [])
        self.assertIn("safety_alert_cleared", events)

    def test_explicit_auto_off_only_after_two_separate_samples(self):
        strip = sample_strip()
        strip["outlets"][0]["temperature_c"] = 86
        sent = []
        m = SafetyMonitor(snapshot_provider=lambda: [], settings_provider=lambda: {
            "alert_auto_off_enabled": True
        }, command_executor=lambda mac, ch, on: sent.append((mac, ch, on)))
        m.evaluate([strip])
        self.assertEqual(sent, [])
        strip["last_info_at"] = (datetime.now(timezone.utc) + timedelta(milliseconds=1)).isoformat()
        m.evaluate([strip])
        self.assertEqual(sent, [(MAC, ch, False) for ch in range(1, 5)])
        m.evaluate([strip])
        self.assertEqual(len(sent), 4)


class NativeCurrentTests(unittest.TestCase):
    def test_native_requests_restrict_channel(self):
        self.assertEqual(power_current_request(4), "up:power_report:4:current")
        with self.assertRaises(ValueError):
            power_current_request(0)

    def test_native_frame_populates_current_without_voltage_confusion(self):
        server = SimpleNamespace(device_metrics=lambda mac: {}, event_bus=None)
        session = DeviceSession(server, object(), ("127.0.0.1", 25000))
        session.boot = BootInfo("lgutap", MAC, MAC, "1.0.66")
        for i in range(1, 5):
            session.outlets[i] = OutletInfo(
                channel=i, relay=False, overload_protection=False, overheat_protection=False,
                power_raw=0, power_w=0.0, energy_wh=0, energy_kwh=0.0, previous_energy_wh=0,
                temperature_c=20, device_status=True, event_code="00", configuration_hex="00000000",
                test_state=0, fixed_value=0,
            )
        session._handle_frame("up:power_report:1:1250")
        self.assertEqual(session.outlets[1].current_a, 1.25)
        self.assertIsNone(session.total_current_a)
        for channel in range(2, 5):
            session._handle_frame(f"up:power_report:{channel}:250")
        self.assertEqual(session.total_current_a, 2.0)
        session._handle_frame("up:power_report:1:224500")
        self.assertEqual(session.voltage_v, 224.5)
        self.assertEqual(session.outlets[1].current_a, 1.25)


if __name__ == "__main__":
    unittest.main()
