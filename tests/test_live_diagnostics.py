import unittest

from voltra_local.protocol import BootInfo, OutletInfo
from voltra_local.tcp_server import DeviceSession


class FakeServer:
    response_timeout = 0.1
    boot_timeout = 1.0


class FakeSocket:
    pass


def outlet(channel: int, relay: bool = False) -> OutletInfo:
    return OutletInfo(
        channel=channel,
        relay=relay,
        overload_protection=False,
        overheat_protection=False,
        power_raw=0,
        power_w=0.0,
        energy_wh=0,
        energy_kwh=0.0,
        previous_energy_wh=0,
        temperature_c=25,
        device_status=True,
        event_code="00",
        configuration_hex="00000000",
        test_state=0,
        fixed_value=0,
    )


class LiveDiagnosticsSessionTests(unittest.TestCase):
    def make_session(self) -> DeviceSession:
        session = DeviceSession(FakeServer(), FakeSocket(), ("127.0.0.1", 12345))
        session.boot = BootInfo(
            model="lgutap",
            mac="D8AA59D28888",
            client_id="D8AA59D28888",
            firmware_version="1.0.66",
        )
        session.outlets[2] = outlet(2, False)
        return session

    def test_voltage_and_rssi_update_snapshot(self):
        session = self.make_session()
        session._handle_frame("up:power_report:1:223400")
        session._handle_frame("up:query:-48")

        snapshot = session.snapshot()
        self.assertEqual(snapshot["voltage_v"], 223.4)
        self.assertEqual(snapshot["wifi_rssi_dbm"], -48)
        self.assertIsNotNone(snapshot["last_diagnostics_at"])

    def test_physical_event_updates_outlet_immediately(self):
        session = self.make_session()
        session._handle_frame("up:event:onoff:2:on")

        snapshot = session.snapshot()
        self.assertTrue(snapshot["outlets"][0]["relay"])
        self.assertEqual(snapshot["last_event"]["type"], "physical_onoff")
        self.assertEqual(snapshot["last_event"]["outlet"], 2)
        self.assertTrue(snapshot["last_event"]["on"])
        self.assertIsNotNone(snapshot["last_event_at"])

    def test_master_event_is_recorded(self):
        session = self.make_session()
        session._handle_frame("up:event:onoff:0:off")

        snapshot = session.snapshot()
        self.assertEqual(snapshot["last_event"]["outlet"], 0)
        self.assertFalse(snapshot["last_event"]["on"])


if __name__ == "__main__":
    unittest.main()
