# Voltra Mobile

Native Android controller for the Voltra Local Mini Server.

## v1.3.0 — secure HTTPS remote access

Permanent Android package ID:

```text
com.ayman.voltra.voltra_mobile
```

v1.3 adds:

- first-class `https://` Voltra server URLs
- optional Bearer access token for protected remote APIs
- access token stored with `flutter_secure_storage`
- authentication error handling for HTTP 401
- public MikroTik URL support without disabling TLS validation
- LAN discovery and intentional local HTTP support remain available
- v1.2 PIN/biometric app lock remains unchanged

v1.1 production identity remains unchanged:

- Voltra launcher icon and adaptive icon
- branded dark Voltra splash screen
- permanent package identity
- app/server version information
- production signing support in GitHub Actions
- deterministic artifact naming with signing mode

Core features remain:

- automatic Voltra-X LAN discovery over UDP 10087
- manual server connection by LAN IP, hostname, or HTTPS URL
- server address and optional API token saved securely on the phone
- live strip dashboard and total power
- four outlet controls per strip
- Turn all on / Turn all off
- energy summary and power-history chart
- recurring schedules
- countdown timers
- one-tap scene execution
- pending-strip adoption
- MTTL-W01 Wi-Fi provisioning form
- local-only operation with no mandatory cloud account

The APK talks to the Voltra API directly on LAN or through the configured HTTPS reverse proxy and the server continues
to own device TCP communication on port 10086.

See `SIGNING.md` for permanent Android signing setup.

## Build

GitHub Actions builds a release APK automatically from `.github/workflows/mobile-apk.yml`.

For local development:

```bash
flutter create /tmp/voltra_mobile --platforms=android --org com.ayman.voltra --project-name voltra_mobile
rm -rf /tmp/voltra_mobile/lib /tmp/voltra_mobile/test /tmp/voltra_mobile/assets
cp -R mobile/lib /tmp/voltra_mobile/lib
cp -R mobile/test /tmp/voltra_mobile/test
cp -R mobile/assets /tmp/voltra_mobile/assets
cp mobile/pubspec.yaml /tmp/voltra_mobile/pubspec.yaml
cp mobile/android/AndroidManifest.xml /tmp/voltra_mobile/android/app/src/main/AndroidManifest.xml
cd /tmp/voltra_mobile
flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create
flutter run
```

Android allows clear-text HTTP only for intentional trusted-LAN use. Remote connections should use a valid HTTPS certificate; the app does not bypass TLS certificate validation.
