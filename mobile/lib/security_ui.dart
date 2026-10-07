import 'package:flutter/material.dart';

import 'security_controller.dart';

class VoltraLockScreen extends StatefulWidget {
  final SecurityController security;
  const VoltraLockScreen({super.key, required this.security});

  @override
  State<VoltraLockScreen> createState() => _VoltraLockScreenState();
}

class _VoltraLockScreenState extends State<VoltraLockScreen> {
  final pin = TextEditingController();
  bool busy = false;
  String? error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && widget.security.biometricEnabled) {
        _useBiometric();
      }
    });
  }

  @override
  void dispose() {
    pin.dispose();
    super.dispose();
  }

  bool _validPin(String value) {
    if (value.length < 4 || value.length > 6) return false;
    return value.codeUnits.every((unit) => unit >= 48 && unit <= 57);
  }

  Future<void> _unlockWithPin() async {
    if (busy) return;
    final value = pin.text.trim();
    if (!_validPin(value)) {
      setState(() => error = 'Enter your 4 to 6 digit PIN.');
      return;
    }

    setState(() {
      busy = true;
      error = null;
    });
    final ok = await widget.security.verifyPin(value);
    if (!mounted) return;
    if (!ok) {
      setState(() {
        busy = false;
        error = 'Incorrect PIN. Try again.';
      });
      pin.clear();
    }
  }

  Future<void> _useBiometric() async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    final ok = await widget.security.authenticateBiometric();
    if (!mounted) return;
    if (!ok) {
      setState(() {
        busy = false;
        error = 'Biometric unlock was not completed.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 430),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: const Color(0xFF39E27D),
                      borderRadius: BorderRadius.circular(21),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x4439E27D),
                          blurRadius: 28,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.bolt_rounded,
                      size: 42,
                      color: Color(0xFF062014),
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Voltra is locked',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Unlock before controlling outlets, schedules, or server settings.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFF8993A7),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: pin,
                    enabled: !busy,
                    autofocus: !widget.security.biometricEnabled,
                    obscureText: true,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 8,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'PIN',
                      hintText: '••••',
                      counterText: '',
                    ),
                    onSubmitted: (_) => _unlockWithPin(),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFFFF8A95)),
                    ),
                  ],
                  const SizedBox(height: 14),
                  FilledButton.icon(
                    onPressed: busy ? null : _unlockWithPin,
                    icon: busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.lock_open_rounded),
                    label: const Text('Unlock Voltra'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                  ),
                  if (widget.security.biometricEnabled) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: busy ? null : _useBiometric,
                      icon: const Icon(Icons.fingerprint_rounded),
                      label: const Text('Use biometrics'),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(50),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  const Text(
                    'Your PIN never leaves this device.',
                    style: TextStyle(
                      color: Color(0xFF7E899E),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class SecuritySettingsCard extends StatelessWidget {
  final SecurityController security;
  const SecuritySettingsCard({super.key, required this.security});

  void _snack(BuildContext context, String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor:
            error ? const Color(0xFF4A1F29) : const Color(0xFF153425),
      ),
    );
  }

  Future<String?> _showSetPinDialog(BuildContext context) async {
    final first = TextEditingController();
    final confirm = TextEditingController();
    String? error;

    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setLocal) => AlertDialog(
          title: const Text('Create Voltra PIN'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Choose a 4 to 6 digit PIN. Biometrics can be enabled after the PIN is created.',
                style: TextStyle(fontSize: 12, height: 1.45),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: first,
                autofocus: true,
                obscureText: true,
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: 'New PIN',
                  counterText: '',
                ),
              ),
              const SizedBox(height: 9),
              TextField(
                controller: confirm,
                obscureText: true,
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: 'Confirm PIN',
                  counterText: '',
                ),
              ),
              if (error != null) ...[
                const SizedBox(height: 8),
                Text(
                  error!,
                  style: const TextStyle(
                    color: Color(0xFFFF8A95),
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final value = first.text.trim();
                final isDigits = value.codeUnits
                    .every((unit) => unit >= 48 && unit <= 57);
                if (value.length < 4 || value.length > 6 || !isDigits) {
                  setLocal(() => error = 'PIN must contain 4 to 6 digits.');
                  return;
                }
                if (value != confirm.text.trim()) {
                  setLocal(() => error = 'PIN confirmation does not match.');
                  return;
                }
                Navigator.pop(dialogContext, value);
              },
              child: const Text('Enable lock'),
            ),
          ],
        ),
      ),
    );

    first.dispose();
    confirm.dispose();
    return result;
  }

  Future<bool> _verifyPin(BuildContext context) async {
    final controller = TextEditingController();
    String? error;
    bool busy = false;

    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setLocal) => AlertDialog(
          title: const Text('Confirm Voltra PIN'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Enter your current PIN to turn off app lock.',
                style: TextStyle(fontSize: 12),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                autofocus: true,
                enabled: !busy,
                obscureText: true,
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: 'Current PIN',
                  counterText: '',
                ),
              ),
              if (error != null) ...[
                const SizedBox(height: 8),
                Text(
                  error!,
                  style: const TextStyle(
                    color: Color(0xFFFF8A95),
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed:
                  busy ? null : () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      setLocal(() {
                        busy = true;
                        error = null;
                      });
                      final ok = await security.verifyPin(
                        controller.text.trim(),
                        unlockOnSuccess: false,
                      );
                      if (!dialogContext.mounted) return;
                      if (ok) {
                        Navigator.pop(dialogContext, true);
                      } else {
                        setLocal(() {
                          busy = false;
                          error = 'Incorrect PIN.';
                        });
                        controller.clear();
                      }
                    },
              child: Text(busy ? 'Checking…' : 'Confirm'),
            ),
          ],
        ),
      ),
    );

    controller.dispose();
    return result == true;
  }

  String _autoLockLabel(int seconds) {
    if (seconds == 0) return 'Immediately';
    if (seconds < 60) return '$seconds seconds';
    if (seconds == 60) return '1 minute';
    return '${seconds ~/ 60} minutes';
  }

  Future<int?> _chooseAutoLock(BuildContext context) {
    const options = <int>[0, 30, 60, 300];
    return showDialog<int>(
      context: context,
      builder: (dialogContext) => SimpleDialog(
        title: const Text('Auto-lock'),
        children: [
          for (final seconds in options)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(dialogContext, seconds),
              child: Row(
                children: [
                  Icon(
                    seconds == security.autoLockSeconds
                        ? Icons.radio_button_checked_rounded
                        : Icons.radio_button_off_rounded,
                    color: seconds == security.autoLockSeconds
                        ? const Color(0xFF39E27D)
                        : const Color(0xFF7E899E),
                  ),
                  const SizedBox(width: 12),
                  Text(_autoLockLabel(seconds)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          SwitchListTile(
            secondary: const Icon(Icons.lock_outline_rounded),
            value: security.enabled,
            title: const Text('Protect Voltra'),
            subtitle: Text(
              security.enabled
                  ? 'PIN is required after Voltra auto-locks.'
                  : 'Add a local PIN before anyone can control your strips.',
            ),
            onChanged: (value) async {
              if (value) {
                final pin = await _showSetPinDialog(context);
                if (pin == null) return;
                try {
                  await security.enableWithPin(pin);
                  if (context.mounted) {
                    _snack(context, 'Voltra app lock enabled.');
                  }
                } catch (e) {
                  if (context.mounted) {
                    _snack(context, e.toString(), error: true);
                  }
                }
                return;
              }

              final confirmed = await _verifyPin(context);
              if (!confirmed) return;
              await security.disable();
              if (context.mounted) {
                _snack(context, 'Voltra app lock disabled.');
              }
            },
          ),
          if (security.enabled) ...[
            const Divider(height: 1),
            SwitchListTile(
              secondary: const Icon(Icons.fingerprint_rounded),
              value: security.biometricEnabled,
              title: const Text('Biometric unlock'),
              subtitle: Text(
                security.canUseBiometrics
                    ? 'Use fingerprint or face authentication on this device.'
                    : 'No supported biometric authentication is available.',
              ),
              onChanged: security.canUseBiometrics
                  ? (value) async {
                      final ok = await security.setBiometricEnabled(value);
                      if (context.mounted && value && !ok) {
                        _snack(
                          context,
                          'Biometric authentication was not completed.',
                          error: true,
                        );
                      }
                    }
                  : null,
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.timer_outlined),
              title: const Text('Auto-lock'),
              subtitle: const Text(
                'Lock Voltra after the app stays in the background.',
              ),
              trailing: Text(_autoLockLabel(security.autoLockSeconds)),
              onTap: () async {
                final seconds = await _chooseAutoLock(context);
                if (seconds != null) {
                  await security.setAutoLockSeconds(seconds);
                }
              },
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.lock_clock_outlined),
              title: const Text('Lock now'),
              subtitle: const Text('Require PIN or biometrics immediately.'),
              onTap: security.lock,
            ),
          ],
        ],
      ),
    );
  }
}
