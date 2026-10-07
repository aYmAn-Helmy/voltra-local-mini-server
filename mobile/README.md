# Voltra Mobile

Native Android controller for the Voltra Local Mini Server.

## v1.1.0 — production identity

Permanent Android package ID:

```text
com.ayman.voltra.voltra_mobile
```

v1.1 adds:

- Voltra launcher icon
- Android adaptive icon
- branded dark Voltra splash screen
- explicit permanent package identity
- app/server version information
- production signing support in GitHub Actions
- deterministic artifact naming with signing mode

Core features remain:

- automatic Voltra-X LAN discovery over UDP 10087
- manual server connection by IP/hostname
- server address saved on the phone
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

The APK talks to the existing Voltra HTTP API on port 8086 and the server continues
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

Android allows clear-text HTTP intentionally because Voltra is designed for a trusted local LAN.
