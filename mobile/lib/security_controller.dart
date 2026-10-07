import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

class SecurityController extends ChangeNotifier {
  SecurityController({
    FlutterSecureStorage? storage,
    LocalAuthentication? auth,
  })  : _storage = storage ?? const FlutterSecureStorage(),
        _auth = auth ?? LocalAuthentication();

  static const _enabledKey = 'voltra.security.enabled';
  static const _pinSaltKey = 'voltra.security.pin_salt';
  static const _pinHashKey = 'voltra.security.pin_hash';
  static const _biometricKey = 'voltra.security.biometric';
  static const _autoLockKey = 'voltra.security.auto_lock_seconds';

  final FlutterSecureStorage _storage;
  final LocalAuthentication _auth;

  bool initialized = false;
  bool enabled = false;
  bool unlocked = true;
  bool biometricEnabled = false;
  bool canUseBiometrics = false;
  int autoLockSeconds = 30;

  DateTime? _backgroundedAt;

  Future<void> initialize() async {
    enabled = await _storage.read(key: _enabledKey) == '1';
    autoLockSeconds =
        int.tryParse(await _storage.read(key: _autoLockKey) ?? '') ?? 30;

    try {
      final supported = await _auth.isDeviceSupported();
      final canCheck = await _auth.canCheckBiometrics;
      canUseBiometrics = supported && canCheck;
    } catch (_) {
      canUseBiometrics = false;
    }

    final storedBiometric = await _storage.read(key: _biometricKey) == '1';
    biometricEnabled = enabled && storedBiometric && canUseBiometrics;
    unlocked = !enabled;
    initialized = true;
    notifyListeners();
  }

  Future<void> enableWithPin(String pin) async {
    _validatePin(pin);
    final saltBytes = List<int>.generate(
      24,
      (_) => Random.secure().nextInt(256),
    );
    final salt = base64UrlEncode(saltBytes);
    final hash = _hashPin(pin, salt);

    await _storage.write(key: _pinSaltKey, value: salt);
    await _storage.write(key: _pinHashKey, value: hash);
    await _storage.write(key: _enabledKey, value: '1');
    await _storage.write(
      key: _autoLockKey,
      value: autoLockSeconds.toString(),
    );

    enabled = true;
    unlocked = true;
    notifyListeners();
  }

  Future<bool> verifyPin(String pin, {bool unlockOnSuccess = true}) async {
    final salt = await _storage.read(key: _pinSaltKey);
    final expected = await _storage.read(key: _pinHashKey);
    if (salt == null || expected == null) return false;

    final ok = _constantTimeEquals(_hashPin(pin, salt), expected);
    if (ok && unlockOnSuccess) {
      unlocked = true;
      _backgroundedAt = null;
      notifyListeners();
    }
    return ok;
  }

  Future<void> disable() async {
    await _storage.delete(key: _enabledKey);
    await _storage.delete(key: _pinSaltKey);
    await _storage.delete(key: _pinHashKey);
    await _storage.delete(key: _biometricKey);
    await _storage.delete(key: _autoLockKey);

    enabled = false;
    unlocked = true;
    biometricEnabled = false;
    _backgroundedAt = null;
    notifyListeners();
  }

  Future<bool> setBiometricEnabled(bool value) async {
    if (!enabled) return false;
    if (value) {
      if (!canUseBiometrics) return false;
      final ok = await _authenticate(
        'Confirm your identity to enable biometric unlock for Voltra.',
      );
      if (!ok) return false;
    }

    biometricEnabled = value;
    await _storage.write(key: _biometricKey, value: value ? '1' : '0');
    notifyListeners();
    return true;
  }

  Future<bool> authenticateBiometric() async {
    if (!enabled || !biometricEnabled || !canUseBiometrics) return false;
    final ok = await _authenticate('Unlock Voltra to control your power strips.');
    if (ok) {
      unlocked = true;
      _backgroundedAt = null;
      notifyListeners();
    }
    return ok;
  }

  Future<void> setAutoLockSeconds(int seconds) async {
    if (seconds < 0) return;
    autoLockSeconds = seconds;
    await _storage.write(key: _autoLockKey, value: seconds.toString());
    notifyListeners();
  }

  void markBackgrounded() {
    if (!enabled || !unlocked) return;
    _backgroundedAt ??= DateTime.now();
  }

  void handleResumed() {
    if (!enabled || !unlocked) {
      _backgroundedAt = null;
      return;
    }

    final backgroundedAt = _backgroundedAt;
    _backgroundedAt = null;
    if (backgroundedAt == null) return;

    final elapsed = DateTime.now().difference(backgroundedAt).inSeconds;
    if (autoLockSeconds == 0 || elapsed >= autoLockSeconds) {
      lock();
    }
  }

  void lock() {
    if (!enabled || !unlocked) return;
    unlocked = false;
    notifyListeners();
  }

  Future<bool> _authenticate(String reason) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }

  static void _validatePin(String pin) {
    if (!RegExp(r'^\d{4,6}$').hasMatch(pin)) {
      throw const FormatException('PIN must contain 4 to 6 digits.');
    }
  }

  static String _hashPin(String pin, String salt) =>
      sha256.convert(utf8.encode('$salt:$pin')).toString();

  static bool _constantTimeEquals(String left, String right) {
    if (left.length != right.length) return false;
    var diff = 0;
    for (var i = 0; i < left.length; i++) {
      diff |= left.codeUnitAt(i) ^ right.codeUnitAt(i);
    }
    return diff == 0;
  }
}
