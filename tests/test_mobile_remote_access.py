from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MobileRemoteAccessSourceTests(unittest.TestCase):
    def test_mobile_version_and_secure_token_storage(self):
        pubspec = (ROOT / "mobile" / "pubspec.yaml").read_text(encoding="utf-8")
        controller = (ROOT / "mobile" / "lib" / "app_controller.dart").read_text(encoding="utf-8")
        api = (ROOT / "mobile" / "lib" / "voltra_api.dart").read_text(encoding="utf-8")
        self.assertIn("version: 1.3.1+5", pubspec)
        self.assertIn("voltra.api.token.secure", controller)
        self.assertIn("FlutterSecureStorage", controller)
        self.assertIn("'authorization': 'Bearer $apiToken'", api)
        self.assertNotIn("badCertificateCallback", api)

    def test_https_is_supported_without_tls_bypass(self):
        api = (ROOT / "mobile" / "lib" / "voltra_api.dart").read_text(encoding="utf-8")
        self.assertIn("https://", api)
        self.assertIn("Uri.tryParse(baseUrl)", api)
        self.assertIn("AndroidNativeHttpClient", api)

    def test_android_native_transport_keeps_tls_verification(self):
        native = (ROOT / "mobile" / "android" / "MainActivity.kt").read_text(encoding="utf-8")
        pubspec = (ROOT / "mobile" / "pubspec.yaml").read_text(encoding="utf-8")
        self.assertIn('enabledProtocols = arrayOf("TLSv1.2")', native)
        self.assertIn('endpointIdentificationAlgorithm = "HTTPS"', native)
        self.assertIn("SSLSocketFactory.getDefault()", native)
        self.assertNotIn("HostnameVerifier", native)
        self.assertNotIn("X509TrustManager", native)
        self.assertNotIn("cronet_http:", pubspec)
        self.assertNotIn("ok_http:", pubspec)


if __name__ == "__main__":
    unittest.main()
