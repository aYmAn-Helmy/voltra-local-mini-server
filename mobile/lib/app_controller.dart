import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:package_info_plus/package_info_plus.dart';

import 'voltra_api.dart';

class AppController extends ChangeNotifier {
  // Legacy v1.1 stored only the server address in Android's preferences.
  // Read it directly from Android when upgrading, without the incompatible
  // shared_preferences Pigeon plugin that crashed during startup on some phones.
  static const _legacyPreferences = MethodChannel('com.ayman.voltra/legacy_preferences');
  static const _secureServerKey = 'voltra.server.secure';
  static const _secureTokenKey = 'voltra.api.token.secure';

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  Future<String?> _readLegacyServer() async {
    if (!Platform.isAndroid) return null;
    try {
      return await _legacyPreferences.invokeMethod<String>('readServer');
    } on PlatformException catch (error) {
      debugPrint('Unable to read legacy server URL: $error');
      return null;
    } on MissingPluginException catch (error) {
      debugPrint('Legacy server bridge unavailable: $error');
      return null;
    }
  }

  Future<void> _clearLegacyServer() async {
    if (!Platform.isAndroid) return;
    try {
      await _legacyPreferences.invokeMethod<void>('clearServer');
    } on PlatformException catch (error) {
      debugPrint('Unable to clear migrated legacy server URL: $error');
    } on MissingPluginException catch (error) {
      debugPrint('Legacy server bridge unavailable: $error');
    }
  }

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
  String appVersion = '—';
  String appBuild = '—';
  Timer? _poller;
  int _activityTick = 0;
  String? _lastAuditKey;
  String? lastAlert;
  int alertSerial = 0;
  List<Map<String, dynamic>> activityFeed = [];
  int _refreshSerial = 0;
  final Map<String, bool> _pendingOutlets = {};
  final Set<String> busyOutlets = {};

  bool outletBusy(String mac, int channel) => busyOutlets.contains("$mac:$channel");

  void _applyOutlet(Map<String, dynamic>? source, String mac, int channel, bool on) {
    if (source == null) return;
    final strips = source["strips"];
    if (strips is! List) return;
    for (final strip in strips) {
      if (strip is! Map || strip["mac"]?.toString() != mac) continue;
      final outlets = strip["outlets"];
      if (outlets is! List) continue;
      for (final outlet in outlets) {
        if (outlet is Map && int.tryParse("${outlet["channel"]}") == channel) {
          outlet["relay"] = on;
          return;
        }
      }
    }
  }

  void _overlayPending(Map<String, dynamic> source) {
    for (final entry in _pendingOutlets.entries) {
      final separator = entry.key.lastIndexOf(":");
      if (separator < 0) continue;
      _applyOutlet(source, entry.key.substring(0, separator), int.parse(entry.key.substring(separator + 1)), entry.value);
    }
  }


  String get baseUrl => api?.baseUrl ?? '';
  bool get apiTokenConfigured => api?.hasApiToken ?? false;
  bool get usingHttps => api?.isHttps ?? false;

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
    final info = await PackageInfo.fromPlatform();
    appVersion = info.version;
    appBuild = info.buildNumber;
    var saved = await _secureStorage.read(key: _secureServerKey);
    // Only ask Android for old unencrypted data if the secure value is absent.
    // This migration happens once; existing secure settings are untouched.
    if (saved == null || saved.isEmpty) {
      final legacy = await _readLegacyServer();
      if (legacy != null && legacy.isNotEmpty) {
        saved = legacy;
        await _secureStorage.write(key: _secureServerKey, value: legacy);
        await _clearLegacyServer();
      }
    }
    if (saved == null || saved.isEmpty) return;
    final savedToken = await _secureStorage.read(key: _secureTokenKey);
    await connect(
      saved,
      apiToken: savedToken ?? '',
      persist: false,
      silent: true,
    );
  }

  Future<void> connect(
    String url, {
    String apiToken = '',
    bool persist = true,
    bool silent = false,
  }) async {
    loading = true;
    if (!silent) error = null;
    notifyListeners();
    VoltraApi? candidate;
    try {
      candidate = VoltraApi(url, apiToken: apiToken);
      await candidate.health();
      await candidate.overview();
      final previous = api;
      api = candidate;
      previous?.close();
      connected = true;
      if (persist) {
        await _secureStorage.write(
          key: _secureServerKey,
          value: candidate.baseUrl,
        );
        if (candidate.apiToken.isEmpty) {
          await _secureStorage.delete(key: _secureTokenKey);
        } else {
          await _secureStorage.write(
            key: _secureTokenKey,
            value: candidate.apiToken,
          );
        }
        await _clearLegacyServer();
      }
      await refresh();
      await refreshActivity(first: true);
      _startPolling();
    } catch (e) {
      if (identical(api, candidate)) {
        api = null;
      }
      candidate?.close();
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
    _refreshSerial++;
    busyOutlets.clear();
    _pendingOutlets.clear();
    final current = api;
    api = null;
    current?.close();
    overview = null;
    connected = false;
    await _secureStorage.delete(key: _secureServerKey);
    await _secureStorage.delete(key: _secureTokenKey);
    await _clearLegacyServer();
    notifyListeners();
  }

  void _startPolling() {
    _poller?.cancel();
    _poller = Timer.periodic(const Duration(seconds: 4), (_) {
      refresh(silent: true);
      if (++_activityTick % 3 == 0) refreshActivity();
    });
  }

  Future<void> refresh({bool silent = false}) async {
    final client = api;
    if (client == null) return;
    final generation = ++_refreshSerial;
    if (!silent) {
      loading = true;
      notifyListeners();
    }
    try {
      final result = await Future.wait([client.overview(), client.automation()]);
      if (generation != _refreshSerial || !identical(client, api)) return;
      final next = result[0];
      _overlayPending(next);
      overview = next;
      automation = result[1];
      connected = true;
      error = null;
    } catch (e) {
      if (generation == _refreshSerial) error = e.toString();
    } finally {
      if (!silent) loading = false;
      notifyListeners();
    }
  }

  Future<bool> _sendOutlet(String mac, int outlet, bool on, {bool confirmProtected = false}) async {
    final client = api;
    if (client == null) throw const VoltraException('Connect to Voltra first.');
    final key = '$mac:$outlet';
    if (busyOutlets.contains(key)) return false;
    busyOutlets.add(key);
    _pendingOutlets[key] = on;
    _refreshSerial++; // Discard stale polls started before this control command.
    _applyOutlet(overview, mac, outlet, on);
    notifyListeners();
    try {
      final result = await client.setOutlet(mac, outlet, on, confirmProtected: confirmProtected);
      final metrics = result['metrics'];
      if (metrics is! Map || metrics['last_command_confirmed'] != true) {
        throw const VoltraException('Command sent, but relay state was not verified. Refresh to check.');
      }
      return true;
    } finally {
      busyOutlets.remove(key);
      _pendingOutlets.remove(key);
      notifyListeners();
    }
  }

  Future<void> setOutlet(String mac, int outlet, bool on, {bool confirmProtected = false}) async {
    try {
      await _sendOutlet(mac, outlet, on, confirmProtected: confirmProtected);
    } finally {
      await refresh(silent: true);
    }
  }

  Future<void> setAll(Map<String, dynamic> strip, bool on) async {
    final mac = strip['mac']?.toString() ?? '';
    if (mac.isEmpty) throw const VoltraException('Missing strip MAC address.');
    final outlets = (strip['outlets'] as List? ?? const []);
    final targets = <int>[];
    for (var channel = 1; channel <= 4; channel++) {
      Map? current;
      for (final item in outlets) {
        if (item is Map && int.tryParse('${item['channel']}') == channel) {
          current = item;
          break;
        }
      }
      if ((current?['relay'] == true) != on) targets.add(channel);
    }
    // Preserve device protocol ordering; avoid four full API refreshes.
    var failures = 0;
    try {
      for (final channel in targets) {
        try {
          if (!await _sendOutlet(mac, channel, on, confirmProtected: !on)) failures++;
        } catch (_) {
          failures++;
        }
      }
    } finally {
      await refresh(silent: true);
    }
    if (failures > 0) {
      throw VoltraException('$failures outlet command(s) failed or could not be verified.');
    }
  }

  Future<void> refreshActivity({bool first = false}) async {
    final client = api;
    if (client == null) return;
    try {
      final payload = await client.auditFeed();
      if (!identical(client, api)) return;
      final events = (payload['events'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
      if (events.isEmpty) return;
      final latest = events.last;
      String fingerprint(Map<String, dynamic> value) =>
          '${value['at']}:${value['category']}:${value['action']}:${value['details']}';
      final key = fingerprint(latest);
      final last = _lastAuditKey;
      _lastAuditKey = key;
      activityFeed = events.reversed
          .where((e) => e['category'] == 'outlet' || (e['category'] == 'automation' && e['action'] == 'rule_fired'))
          .take(50)
          .toList();
      if (first || last == null || last == key) {
        notifyListeners();
        return;
      }
      var foundLast = false;
      final unseen = <Map<String, dynamic>>[];
      for (final item in events.reversed) {
        if (fingerprint(item) == last) {
          foundLast = true;
          break;
        }
        unseen.add(item);
      }
      if (!foundLast) {
        // Lost history between polls: do not replay old commands as new alerts.
        notifyListeners();
        return;
      }
      for (final item in unseen.reversed) {
        final details = item['details'];
        if (details is! Map) continue;
        final action = item['action']?.toString() ?? '';
        final mac = details['mac']?.toString() ?? '';
        final channel = int.tryParse('${details['outlet']}');
        if (channel == null) continue;
        if (item['category'] != 'outlet' && action != 'rule_fired') continue;
        final matching = strips.where((x) => x['mac'] == mac).toList();
        if (matching.isEmpty) continue;
        final prefs = matching.first['outlet_preferences'];
        if (prefs is Map && (prefs['$channel'] as Map?)?['notify'] == false) continue;
        final name = ((prefs is Map ? (prefs['$channel'] as Map?)?['name'] : null) ??
            'المخرج $channel').toString();
        lastAlert = action == 'power_on'
            ? 'تم تشغيل $name'
            : action == 'power_off'
                ? 'تم إيقاف $name'
                : action == 'rule_fired'
                    ? 'تنبيه استهلاك: $name'
                    : 'تم تعديل إعدادات $name';
        alertSerial++;
      }
      notifyListeners();
    } catch (_) {
      // Alerts must never block relay control or normal screen refresh.
    }
  }

  Future<void> renameStrip(String mac, String name) async {
    if (name.trim().isEmpty) throw const VoltraException('اسم المشترك مطلوب');
    await api?.renameStrip(mac, name.trim());
    await refresh(silent: true);
  }

  Future<Map<String, dynamic>> getOutletPrefs(String mac, int channel) async {
    final client = api;
    if (client == null) throw const VoltraException('Server not connected.');
    return client.getOutletPrefs(mac, channel);
  }

  Future<void> saveOutletPrefs(String mac, int channel, Map<String, dynamic> changes) async {
    final client = api;
    if (client == null) throw const VoltraException('Server not connected.');
    await client.saveOutletPrefs(mac, channel, changes);
    await refresh(silent: true);
  }

  Future<List<Map<String, dynamic>>> outletActivity(String mac, int channel) async {
    final client = api;
    if (client == null) throw const VoltraException('Server not connected.');
    final result = await client.outletActivity(mac, channel);
    final items = result['events'];
    if (items is! List) return [];
    return items.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
  }

  Future<void> createScene(String name, String mac, int channel, bool on) async {
    final client = api;
    if (client == null) throw const VoltraException('Server not connected.');
    await client.createScene(name, mac, channel, on);
    await refresh(silent: true);
  }

  Future<void> adopt(String mac, String name) async {
    await api?.adoptStrip(mac, name);
    await refresh(silent: true);
  }

  Future<void> ignore(String mac) async {
    await api?.ignoreStrip(mac);
    await refresh(silent: true);
  }

  Future<Map<String, dynamic>> provision({
    required String ssid,
    required String password,
    required String serverIp,
    String deviceIp = '192.168.1.1',
  }) async {
    return VoltraApi.provisionDirect(
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
    api?.close();
    api = null;
    super.dispose();
  }
}
