import tempfile
import unittest
from pathlib import Path

from voltra_local.store import ConfigStore


class StoreBackupTests(unittest.TestCase):
    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = ConfigStore(Path(tmp) / "one.json")
            first.record_strip({
                "mac": "D8AA59D28888",
                "model": "lgutap",
                "firmware_version": "1.0.66",
                "remote_address": "192.168.1.20:10086",
            })
            first.adopt_strip("D8AA59D28888", "Main Strip")
            backup = first.export_data()

            second = ConfigStore(Path(tmp) / "two.json")
            second.import_data(backup)
            restored = second.strip("D8AA59D28888")
            self.assertEqual(restored["name"], "Main Strip")
            self.assertTrue(restored["managed"])


if __name__ == "__main__":
    unittest.main()
