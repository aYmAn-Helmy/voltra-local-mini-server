import unittest
from types import SimpleNamespace

from voltra_local.protocol import BootInfo, OutletInfo
from voltra_local.tcp_server import DeviceSession


MAC = "D8AA59D28888"


def make_outlet(relay=False):
    return OutletInfo(
        channel=1, relay=relay,
        overload_protection=False, overheat_protection=False,
        power_raw=0, power_w=0.0,
        energy_wh=0, energy_kwh=0.0, previous_energy_wh=0,
        temperature_c=25, device_status=True, event_code="00",
        configuration_hex="00000000", test_state=0, fixed_value=0,
    )


def new_session():
    server = SimpleNamespace(
        command_attempts=1, confirm_delay=0.0,
        device_metrics=lambda mac: {},
        audit=None, event_bus=None,
    )
    session = DeviceSession(server, object(), ("127.0.0.1", 12000))
    session.boot = BootInfo("lgutap", MAC, MAC, "1.0.66")
    session.outlets[1] = make_outlet(False)
    return session


class FastControlTests(unittest.TestCase):
    def test_ack_and_verified_getinfo_update_metrics(self):
        session = new_session()

        def ack(cmd, predicate):
            self.assertEqual(cmd, "up:onoff:1:on")
            return cmd

        def getinfo():
            session.outlets[1].relay = True

        session.request = ack
        session.query_info = getinfo
        result = session.set_outlet(1, True)
        self.assertTrue(result["outlets"][0]["relay"])
        self.assertTrue(result["metrics"]["last_command_confirmed"])
        self.assertGreaterEqual(result["metrics"]["last_control_ack_ms"], 0)
        self.assertGreaterEqual(result["metrics"]["last_control_total_ms"], 0)
        self.assertFalse(session._control_pending.is_set())

    def test_ack_only_does_not_fake_verification(self):
        session = new_session()
        session.request = lambda cmd, predicate: cmd

        def query_fails():
            raise TimeoutError("getinfo missing")

        session.query_info = query_fails
        result = session.set_outlet(1, True)
        self.assertFalse(result["metrics"]["last_command_confirmed"])
        self.assertFalse(result["outlets"][0]["relay"])
        self.assertFalse(session._control_pending.is_set())

    def test_bad_channel_does_not_lock_polling(self):
        session = new_session()
        with self.assertRaises(ValueError):
            session.set_outlet(9, True)
        self.assertFalse(session._control_pending.is_set())


if __name__ == "__main__":
    unittest.main()
