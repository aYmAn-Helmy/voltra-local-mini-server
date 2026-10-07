# Voltra Mobile

Native Android controller for the Voltra Local Mini Server.

## v1.0.0

Features:

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

## Build

GitHub Actions builds a release APK automatically from `.github/workflows/mobile-apk.yml`.

For local development:

```bash
flutter create /tmp/voltra_mobile --platforms=android --org com.ayman.voltra --project-name voltra_mobile
rm -rf /tmp/voltra_mobile/lib
cp -R mobile/lib /tmp/voltra_mobile/lib
cp mobile/pubspec.yaml /tmp/voltra_mobile/pubspec.yaml
cp mobile/android/AndroidManifest.xml /tmp/voltra_mobile/android/app/src/main/AndroidManifest.xml
cd /tmp/voltra_mobile
flutter pub get
flutter run
```

Android allows clear-text HTTP intentionally because Voltra is designed for a trusted local LAN.
