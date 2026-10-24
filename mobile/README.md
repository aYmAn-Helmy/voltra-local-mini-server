# Voltra Mobile

Native Android controller for the Voltra Local Mini Server.

## v1.5.0 — Modern Smart Home + real interactions

ModernSmartHomeUI-inspired device cards with animated on/off states, a tactile
pressed state, haptic confirmations, animated relay progress, and verified
server feedback. These are custom Flutter components wired to the live
Voltra API, **not** sample switches holding local demo values.

- Home quick actions now navigate to Consumption and Automation, or display
  a functional room filter; every tile has ripple, press scale and haptics.
- Outlet cards show pending, unavailable, on and off independently; double
  taps while pending and overlapping group commands are blocked.
- Bulk commands retain confirmation and show a verified result or error.
- Automation action cards show a pending indicator during actual operations.
- Real connection settings, HTTPS token, local provisioning, schedules,
  scenes, PIN and biometric unlock remain in place.
- Maintains v1.4.1 Android startup fix (no shared_preferences Pigeon runtime).

**Attribution:** Visual inspiration from Mitch Koko's ModernSmartHomeUI,
licensed MIT. See `THIRD_PARTY.md`. UI controls were implemented directly
in Voltra rather than importing old Flutter 2 code.



## v1.4.1 — Android startup crash fix

The initial v1.4.0+7 test-signed APK could display a red `NoSuchMethodError`
for `SharedPreferencesApiRegistrar.getAll` at startup on real Android devices.
The fix removes `shared_preferences` / `shared_preferences_android` entirely
from the APK. Saved server address and API token continue to use
`flutter_secure_storage`. An Android platform-channel bridge reads the
pre-v1.2 legacy `FlutterSharedPreferences` URL once (key
`flutter.voltra.server`) and deletes it after saving the value securely.
The PIN/biometric unlock, existing HTTPS connection, provisioning, controls
and all other features are retained.

A release APK smoke check should ensure that launching on Android reaches
the connection/setup or existing dashboard screen without a platform error.

**Important:** Test-signed PR APKs may not be signed with the same key as an
already installed build. An Android `INSTALL_FAILED_UPDATE_INCOMPATIBLE` is
a signing mismatch, not a server issue. Preserve URL/token/PIN details before
uninstalling an older test-signed app.

## v1.3.2 — direct strip provisioning from Android

v1.3.2 fixes new-strip onboarding when the Voltra server is Ethernet-only. The Android phone now talks directly to the MTTL-W01 setup service on `192.168.1.1:30300` while the phone is connected to the temporary `TONLY_TAP...` Wi-Fi. It sends the Voltra server LAN IP first and the target 2.4 GHz Wi-Fi credentials second, using a fresh TCP connection for each command.

The server-side provisioning API remains available for hosts that can themselves reach the strip setup AP.

## v1.3.1 / v1.3.0 — secure HTTPS remote access

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
- direct MTTL-W01 Wi-Fi provisioning from the Android phone while connected to TONLY_TAP
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
