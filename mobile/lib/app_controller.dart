import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'voltra_api.dart';

class AppController extends ChangeNotifier {
  static const _serverKey = 'voltra.server';

  VoltraApi? api;
  Map<String, dynamic>? overview;
  Map<String, dynamic> automation = {
    'schedules': <String, dynamic>{},
    'rules': <String, dynamic>{},
    'queue': <dynamic>[],
  };

  bool loading = false;
  bool connected = false;
  String? error;
  Timer? _poller;

  String get baseUrl => api?.baseUrl ?? '';

  List<Map<String, dynamic>> get strips {
    final raw = overview?['strips'];
    if (raw is! List) return [];
    return raw
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  List<Map<String, dynamic>> get activeStrips => strips
      .where((s) =>
          s['managed'] == true &&
          (s['state'] == 'active' || s['state'] == 'disabled'))
      .toList();

  List<Map<String, dynamic>> get pendingStrips =>
      strips.where((s) => s['state'] == 'pending').toList();

  List<Map<String, dynamic>> get scenes {
    final raw = overview?['scenes'];
    if (raw is! List) return [];
    return raw
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Map<String, dynamic> get summary =>
      Map<String, dynamic>.from(overview?['summary'] as Map? ?? const {});

  String get version => overview?['version']?.toString() ?? '—';

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_serverKey);
    if (saved == null || saved.isEmpty) return;
    await connect(saved, persist: false, silent: true);
  }

  Future<void> connect(
    String url, {
    bool persist = true,
    bool silent = false,
  }) async {
    loading = true;
    if (!silent) error = null;
    notifyListeners();
    try {
      final candidate = VoltraApi(url);
      await candidate.health();
      api = candidate;
      connected = true;
      if (persist) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_serverKey, candidate.baseUrl);
      }
      await refresh();
      _startPolling();
    } catch (e) {
      connected = false;
      if (!silent) error = e.toString();
      if (silent) api = null;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> disconnect() async {
    _poller?.cancel();
    _poller = null;
    api = null;
    overview = null;
    connected = false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_serverKey);
    notifyListeners();
  }

  void _startPolling() {
    _poller?.cancel();
    _poller = Timer.periodic(const Duration(seconds: 4), (_) {
      refresh(silent: true);
    });
  }

  Future<void> refresh({bool silent = false}) async {
    final client = api;
    if (client == null) return;
    if (!silent) {
      loading = true;
      notifyListeners();
    }
    try {
      final result = await Future.wait([
        client.overview(),
        client.automation(),
      ]);
      overview = result[0];
      automation = result[1];
      connected = true;
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      if (!silent) loading = false;
      notifyListeners();
    }
  }

  Future<void> setOutlet(String mac, int outlet, bool on) async {
    final client = api;
    if (client == null) return;
    await client.setOutlet(mac, outlet, on);
    await refresh(silent: true);
  }

  Future<void> setAll(Map<String, dynamic> strip, bool on) async {
    final mac = strip['mac']?.toString() ?? '';
    final outlets = (strip['outlets'] as List? ?? const []);
    for (var channel = 1; channel <= 4; channel++) {
      Map? current;
      for (final item in outlets) {
        if (item is Map && int.tryParse('${item['channel']}') == channel) {
          current = item;
          break;
        }
      }
      if ((current?['relay'] == true) == on) continue;
      await setOutlet(mac, channel, on);
    }
  }

  Future<void> adopt(String mac, String name) async {
    await api?.adoptStrip(mac, name);
    await refresh(silent: true);
  }

  Future<void> ignore(String mac) async {
    await api?.ignoreStrip(mac);
    await refresh(silent: true);
  }

  Future<void> provision({
    required String ssid,
    required String password,
    required String serverIp,
    String deviceIp = '192.168.1.1',
  }) async {
    await api?.provision(
      ssid: ssid,
      password: password,
      serverIp: serverIp,
      deviceIp: deviceIp,
    );
  }

  Future<void> createSchedule(Map<String, dynamic> value) async {
    await api?.createSchedule(value);
    await refresh(silent: true);
  }

  Future<void> createCountdown(Map<String, dynamic> value) async {
    await api?.createCountdown(value);
    await refresh(silent: true);
  }

  Future<void> deleteSchedule(String id) async {
    await api?.deleteSchedule(id);
    await refresh(silent: true);
  }

  Future<void> runScene(String id) async {
    await api?.runScene(id);
    await refresh(silent: true);
  }

  Future<Map<String, dynamic>> energy(
    String mac,
    double hours, {
    int? outlet,
  }) async {
    final client = api;
    if (client == null) throw const VoltraException('Server is not connected.');
    final result = await Future.wait([
      client.energySummary(mac, hours, outlet: outlet),
      client.energyHistory(mac, hours, outlet: outlet),
    ]);
    return {'summary': result[0], 'history': result[1]};
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }
}
