import socket
import unittest
from unittest.mock import patch

from voltra_local.provisioner import ProvisioningError, provision_device


class FakeSocket:
    def __init__(self, response: bytes):
        self.response = response
        self.sent = b""
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def setsockopt(self, *args):
        return None

    def sendall(self, payload):
        self.sent += payload

    def recv(self, size):
        response, self.response = self.response[:size], self.response[size:]
        return response


class ProvisionerTests(unittest.TestCase):
    def test_each_command_uses_its_own_connection(self):
        sockets = [
            FakeSocket(b"up:ip:ip_ok\r\n"),
            FakeSocket(b"up:connect:connect_ok\r\n"),
        ]
        with patch("voltra_local.provisioner.socket.create_connection", side_effect=sockets) as connect:
            result = provision_device(
                ssid="CafeWiFi",
                password="secret123",
                server_ip="192.168.1.50",
                attempts=1,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(sockets[0].sent, b"up:ip:192.168.1.50\r\n")
        self.assertEqual(sockets[1].sent, b"up:connect:CafeWiFi:secret123\r\n")
        self.assertNotIn("secret123", str(result))

    def test_retries_transport_failure_then_succeeds(self):
        success_one = FakeSocket(b"up:ip:ip_ok\r\n")
        success_two = FakeSocket(b"up:connect:connect_ok\r\n")
        with patch(
            "voltra_local.provisioner.socket.create_connection",
            side_effect=[socket.timeout("timed out"), success_one, success_two],
        ) as connect, patch("voltra_local.provisioner.time.sleep"):
            result = provision_device(
                ssid="CafeWiFi",
                password="secret123",
                server_ip="192.168.1.50",
                attempts=3,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(connect.call_count, 3)
        self.assertEqual(result["responses"][0]["attempt"], 2)

    def test_retries_unexpected_reply_and_then_fails(self):
        sockets = [FakeSocket(b"bad\r\n"), FakeSocket(b"still_bad\r\n")]
        with patch("voltra_local.provisioner.socket.create_connection", side_effect=sockets), patch(
            "voltra_local.provisioner.time.sleep"
        ):
            with self.assertRaises(ProvisioningError):
                provision_device(
                    ssid="CafeWiFi",
                    password="secret123",
                    server_ip="192.168.1.50",
                    attempts=2,
                )

    def test_rejects_protocol_delimiter_in_password(self):
        with self.assertRaises(ValueError):
            provision_device(
                ssid="CafeWiFi",
                password="bad:password",
                server_ip="192.168.1.50",
            )

    def test_rejects_ipv6_server_address(self):
        with self.assertRaises(ValueError):
            provision_device(
                ssid="CafeWiFi",
                password="secret123",
                server_ip="::1",
            )


if __name__ == "__main__":
    unittest.main()
