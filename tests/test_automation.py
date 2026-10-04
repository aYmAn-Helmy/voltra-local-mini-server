import tempfile
import unittest
from pathlib import Path

from voltra_local.automation import AutomationEngine


MAC = "D8AA59D28888"


class AutomationTests(unittest.TestCase):
    def make_engine(self):
        self.calls = []
        self.devices = []

        def provider():
            return list(self.devices)

        def execute(mac, outlet, on, source):
            self.calls.append((mac, outlet, on, source))
            return {"ok": True}

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        engine = AutomationEngine(
            Path(temp.name) / "automation.json",
            snapshot_provider=provider,
            command_executor=execute,
        )
        return engine

    def test_create_schedule(self):
        engine = self.make_engine()
        item = engine.create_schedule({
            "mac": MAC,
            "outlet": 2,
            "on": False,
            "time": "23:30",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "offline_policy": "queue",
        })
        self.assertEqual(item["mac"], MAC)
        self.assertEqual(item["outlet"], 2)
        self.assertEqual(len(engine.snapshot()["schedules"]), 1)

    def test_offline_command_is_queued_then_drained(self):
        engine = self.make_engine()
        engine._execute_or_queue(
            MAC,
            1,
            False,
            source="test",
            offline_policy="queue",
            max_queue_age_minutes=10,
            snapshots=[],
        )
        self.assertEqual(len(engine.snapshot()["queue"]), 1)

        engine._drain_queue([{"mac": MAC, "online": True}])
        self.assertEqual(len(engine.snapshot()["queue"]), 0)
        self.assertEqual(self.calls[0][:3], (MAC, 1, False))

    def test_low_power_rule_matches(self):
        engine = self.make_engine()
        rule = engine.create_rule({
            "mac": MAC,
            "outlet": 1,
            "condition": "low_power",
            "threshold": 3,
            "duration_s": 10,
            "action": {"type": "audit"},
        })
        self.assertTrue(engine._rule_matches(rule, {
            "mac": MAC,
            "outlets": [{"channel": 1, "power_w": 1.5}],
        }))

    def test_import_export(self):
        engine = self.make_engine()
        engine.create_rule({
            "mac": MAC,
            "condition": "weak_wifi",
            "threshold": -75,
            "action": {"type": "audit"},
        })
        backup = engine.snapshot()
        engine.import_data(backup)
        self.assertEqual(len(engine.snapshot()["rules"]), 1)


if __name__ == "__main__":
    unittest.main()
