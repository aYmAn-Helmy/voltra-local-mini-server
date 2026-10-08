import unittest

from voltra_local.security import RemoteAccessSecurity


class RemoteAccessSecurityTests(unittest.TestCase):
    def test_tokenless_mode_is_backward_compatible(self):
        policy = RemoteAccessSecurity()
        self.assertFalse(policy.enabled)
        self.assertTrue(policy.authorized(None))
        self.assertTrue(policy.authorized("Bearer anything"))

    def test_bearer_token_required_and_compared(self):
        policy = RemoteAccessSecurity("a" * 43)
        self.assertTrue(policy.enabled)
        self.assertFalse(policy.authorized(None))
        self.assertFalse(policy.authorized("Basic abc"))
        self.assertFalse(policy.authorized("Bearer " + ("b" * 43)))
        self.assertTrue(policy.authorized("Bearer " + ("a" * 43)))

    def test_forwarded_headers_only_from_trusted_proxy(self):
        policy = RemoteAccessSecurity("", "192.168.1.7/32,10.0.0.0/8")
        self.assertEqual(
            policy.client_ip("192.168.1.7", "156.216.159.2, 192.168.1.7"),
            "156.216.159.2",
        )
        self.assertEqual(
            policy.client_ip("192.168.1.45", "156.216.159.2"),
            "192.168.1.45",
        )
        self.assertEqual(policy.request_scheme("192.168.1.7", "https"), "https")
        self.assertEqual(policy.request_scheme("192.168.1.45", "https"), "http")

    def test_invalid_trusted_proxy_is_rejected(self):
        with self.assertRaises(ValueError):
            RemoteAccessSecurity("", "not-a-network")


if __name__ == "__main__":
    unittest.main()
