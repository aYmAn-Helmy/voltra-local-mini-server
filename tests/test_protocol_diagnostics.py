import unittest

from voltra_local.protocol import (
    parse_event_onoff,
    parse_power_report,
    parse_wifi_rssi,
)


class DiagnosticsProtocolTests(unittest.TestCase):
    def test_parse_voltage_power_report(self):
        self.assertEqual(parse_power_report("up:power_report:1:223400"), (1, 223400))

    def test_parse_wifi_rssi(self):
        self.assertEqual(parse_wifi_rssi("up:query:-52"), -52)

    def test_reject_invalid_wifi_rssi(self):
        self.assertIsNone(parse_wifi_rssi("up:query:1"))
        self.assertIsNone(parse_wifi_rssi("up:query:-128"))

    def test_parse_physical_outlet_event(self):
        self.assertEqual(parse_event_onoff("up:event:onoff:2:on"), (2, True))
        self.assertEqual(parse_event_onoff("up:event:onoff:4:off"), (4, False))

    def test_parse_master_event(self):
        self.assertEqual(parse_event_onoff("up:event:onoff:0:off"), (0, False))


if __name__ == "__main__":
    unittest.main()
