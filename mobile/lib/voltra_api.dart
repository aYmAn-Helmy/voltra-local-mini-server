import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'android_native_http_client.dart';

class VoltraException implements Exception {
  final String message;
  final int? statusCode;
  const VoltraException(this.message, [this.statusCode]);

  @override
  String toString() => message;
}

class ServerCandidate {
  final String host;
  final int httpPort;
  final int tcpPort;
  final String name;
  final String version;

  const ServerCandidate({
    required this.host,
    required this.httpPort,
    required this.tcpPort,
    required this.name,
    required this.version,
  });

  String get baseUrl => 'http://$host:$httpPort';
}

class VoltraApi {
  VoltraApi(
    String baseUrl, {
    String? apiToken,
    http.Client? client,
  })  : baseUrl = _normalize(baseUrl),
        apiToken = apiToken?.trim() ?? '',
        _client = client ?? _buildClient();

  final String baseUrl;
  final String apiToken;
  final http.Client _client;

  bool get hasApiToken => apiToken.isNotEmpty;
  bool get isHttps => Uri.tryParse(baseUrl)?.scheme.toLowerCase() == 'https';

  Map<String, String> _headers({bool json = false}) => {
        if (json) 'content-type': 'application/json',
        if (apiToken.isNotEmpty) 'authorization': 'Bearer $apiToken',
      };
  static const _magic = 'VOLTRAX_DISCOVER';

  static http.Client _buildClient() {
    if (Platform.isAndroid) {
      return AndroidNativeHttpClient();
    }
    return http.Client();
  }

  static String _normalize(String value) {
    var result = value.trim();
    if (result.isEmpty) return result;
    if (!result.startsWith('http://') && !result.startsWith('https://')) {
      result = 'http://$result';
    }
    while (result.endsWith('/')) {
      result = result.substring(0, result.length - 1);
    }
    return result;
  }

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$baseUrl$path').replace(queryParameters: query);

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, String>? query,
  }) async {
    final response = await _client
        .get(_uri(path, query), headers: _headers())
        .timeout(const Duration(seconds: 8));
    return _decode(response);
  }

  Future<Map<String, dynamic>> sendJson(
    String method,
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    final encoded = jsonEncode(body ?? <String, dynamic>{});
    late http.Response response;
    final uri = _uri(path);
    final headers = _headers(json: true);
    switch (method.toUpperCase()) {
      case 'POST':
        response = await _client
            .post(uri, headers: headers, body: encoded)
            .timeout(const Duration(seconds: 10));
        break;
      case 'PUT':
        response = await _client
            .put(uri, headers: headers, body: encoded)
            .timeout(const Duration(seconds: 10));
        break;
      case 'DELETE':
        response = await _client
            .delete(uri, headers: headers, body: encoded)
            .timeout(const Duration(seconds: 10));
        break;
      default:
        throw const VoltraException('Unsupported request method.');
    }
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    Map<String, dynamic> payload = <String, dynamic>{};
    if (response.body.trim().isNotEmpty) {
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) {
          payload = decoded;
        } else {
          payload = {'data': decoded};
        }
      } catch (_) {
        payload = {'error': response.body.trim()};
      }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final fallback = response.statusCode == 401
          ? 'Authentication required. Check the Voltra access token.'
          : 'Request failed (${response.statusCode}).';
      throw VoltraException(
        payload['error']?.toString() ?? fallback,
        response.statusCode,
      );
    }
    return payload;
  }

  Future<Map<String, dynamic>> health() => getJson('/health');
  Future<Map<String, dynamic>> overview() =>
      getJson('/voltra/api/overview');
  Future<Map<String, dynamic>> automation() =>
      getJson('/voltra/api/automation');

  Future<Map<String, dynamic>> setOutlet(
    String mac,
    int outlet,
    bool on,
  ) =>
      sendJson(
        'POST',
        '/voltra/api/strips/${Uri.encodeComponent(mac)}/outlets/$outlet/state',
        {'on': on},
      );

  Future<Map<String, dynamic>> adoptStrip(String mac, String name) =>
      sendJson(
        'POST',
        '/voltra/api/strips/${Uri.encodeComponent(mac)}/adopt',
        {'name': name},
      );

  Future<Map<String, dynamic>> ignoreStrip(String mac) =>
      sendJson(
        'POST',
        '/voltra/api/strips/${Uri.encodeComponent(mac)}/ignore',
      );

  Future<Map<String, dynamic>> provision({
    required String ssid,
    required String password,
    required String serverIp,
    String deviceIp = '192.168.1.1',
  }) =>
      sendJson('POST', '/voltra/api/provision', {
        'ssid': ssid,
        'password': password,
        'server_ip': serverIp,
        'device_ip': deviceIp,
      });

  Future<Map<String, dynamic>> createSchedule(
    Map<String, dynamic> value,
  ) =>
      sendJson('POST', '/voltra/api/schedules', value);

  Future<Map<String, dynamic>> createCountdown(
    Map<String, dynamic> value,
  ) =>
      sendJson('POST', '/voltra/api/countdown', value);

  Future<Map<String, dynamic>> deleteSchedule(String id) =>
      sendJson(
        'DELETE',
        '/voltra/api/schedules/${Uri.encodeComponent(id)}',
      );

  Future<Map<String, dynamic>> runScene(String id) =>
      sendJson(
        'POST',
        '/voltra/api/scenes/${Uri.encodeComponent(id)}/run',
      );

  Future<Map<String, dynamic>> energySummary(
    String mac,
    double hours, {
    int? outlet,
  }) =>
      getJson(
        '/voltra/api/energy',
        query: {
          'mac': mac,
          'hours': hours.toString(),
          if (outlet != null) 'outlet': outlet.toString(),
        },
      );

  Future<Map<String, dynamic>> energyHistory(
    String mac,
    double hours, {
    int? outlet,
  }) =>
      getJson(
        '/voltra/api/energy/history',
        query: {
          'mac': mac,
          'hours': hours.toString(),
          'limit': '96',
          if (outlet != null) 'outlet': outlet.toString(),
        },
      );


  static void _validateProvisioningFields({
    required String ssid,
    required String password,
    required String serverIp,
    required String deviceIp,
    required int port,
  }) {
    if (ssid.isEmpty || ssid.length > 64) {
      throw const VoltraException('Wi-Fi SSID is required and must be 64 characters or fewer.');
    }
    if (password.length > 128) {
      throw const VoltraException('Wi-Fi password is too long.');
    }
    for (final value in [ssid, password]) {
      if (value.contains(':') || value.contains('\r') || value.contains('\n')) {
        throw const VoltraException(
          'Wi-Fi name/password cannot contain colon or line-break characters for this strip.',
        );
      }
    }
    final server = InternetAddress.tryParse(serverIp);
    if (server == null || server.type != InternetAddressType.IPv4) {
      throw const VoltraException('Voltra server IP must be a valid IPv4 address.');
    }
    final device = InternetAddress.tryParse(deviceIp);
    if (device == null || device.type != InternetAddressType.IPv4) {
      throw const VoltraException('Strip setup IP must be a valid IPv4 address.');
    }
    if (port < 1 || port > 65535) {
      throw const VoltraException('Strip setup port is invalid.');
    }
  }

  static Future<String> _setupExchange({
    required String deviceIp,
    required int port,
    required String command,
    required Duration timeout,
  }) async {
    Socket? socket;
    try {
      socket = await Socket.connect(deviceIp, port, timeout: timeout);
      socket.setOption(SocketOption.tcpNoDelay, true);
      socket.write('$command\r\n');
      await socket.flush();

      final bytes = <int>[];
      await for (final chunk in socket.timeout(timeout)) {
        bytes.addAll(chunk);
        if (bytes.length >= 2048 || chunk.contains(10)) break;
      }
      return utf8
          .decode(bytes.take(2048).toList(), allowMalformed: true)
          .replaceAll(RegExp(r'[\x00\r\n ]+\$'), '')
          .trim();
    } on TimeoutException {
      throw const VoltraException(
        'Timed out talking to the strip. Make sure the phone is connected to its TONLY_TAP Wi-Fi.',
      );
    } on SocketException catch (e) {
      throw VoltraException(
        'Cannot reach the strip setup service at $deviceIp:$port. '
        'Connect this phone to the strip TONLY_TAP Wi-Fi first. (${e.message})',
      );
    } finally {
      socket?.destroy();
    }
  }

  /// Provision an MTTL-W01 directly from the Android phone.
  ///
  /// The phone must be connected to the strip temporary TONLY_TAP Wi-Fi.
  /// Each setup command uses a fresh TCP connection because the setup service
  /// is short-lived and the original device protocol expects this sequence.
  static Future<Map<String, dynamic>> provisionDirect({
    required String ssid,
    required String password,
    required String serverIp,
    String deviceIp = '192.168.1.1',
    int port = 30300,
    Duration timeout = const Duration(seconds: 3),
    int attempts = 3,
  }) async {
    final cleanSsid = ssid.trim();
    final cleanServerIp = serverIp.trim();
    final cleanDeviceIp = deviceIp.trim();

    _validateProvisioningFields(
      ssid: cleanSsid,
      password: password,
      serverIp: cleanServerIp,
      deviceIp: cleanDeviceIp,
      port: port,
    );
    if (attempts < 1 || attempts > 10) {
      throw const VoltraException('Provisioning retry count is invalid.');
    }

    final steps = <(String, String, String)>[
      ('server_ip', 'up:ip:$cleanServerIp', 'ip_ok'),
      ('wifi', 'up:connect:$cleanSsid:$password', 'connect_ok'),
    ];
    final responses = <Map<String, dynamic>>[];

    for (final step in steps) {
      VoltraException? lastError;
      String response = '';
      var completed = false;

      for (var attempt = 1; attempt <= attempts; attempt++) {
        try {
          response = await _setupExchange(
            deviceIp: cleanDeviceIp,
            port: port,
            command: step.$2,
            timeout: timeout,
          );
          if (response.contains(step.$3)) {
            responses.add({
              'step': step.$1,
              'ok': true,
              'attempt': attempt,
              'response': response,
            });
            completed = true;
            break;
          }
          lastError = VoltraException(
            '${step.$1} returned an unexpected response: '
            '${response.isEmpty ? '<empty>' : response}',
          );
        } on VoltraException catch (e) {
          lastError = e;
        }

        if (attempt < attempts) {
          await Future<void>.delayed(const Duration(milliseconds: 800));
        }
      }

      if (!completed) {
        throw VoltraException(
          '${step.$1} failed after $attempts attempts. '
          '${lastError?.message ?? response}',
        );
      }
    }

    return {
      'ok': true,
      'device_ip': cleanDeviceIp,
      'server_ip': cleanServerIp,
      'responses': responses,
    };
  }

  void close() => _client.close();

  static Future<List<ServerCandidate>> discover({
    Duration timeout = const Duration(seconds: 2),
    int port = 10087,
  }) async {
    final socket = await RawDatagramSocket.bind(
      InternetAddress.anyIPv4,
      0,
      reuseAddress: true,
    );
    socket.broadcastEnabled = true;
    final results = <String, ServerCandidate>{};
    final done = Completer<void>();
    final timer = Timer(timeout, () {
      if (!done.isCompleted) done.complete();
    });

    socket.send(
      utf8.encode(_magic),
      InternetAddress('255.255.255.255'),
      port,
    );

    late StreamSubscription<RawSocketEvent> sub;
    sub = socket.listen((event) {
      if (event != RawSocketEvent.read) return;
      Datagram? datagram;
      while ((datagram = socket.receive()) != null) {
        try {
          final decoded = jsonDecode(utf8.decode(datagram!.data));
          if (decoded is! Map<String, dynamic>) continue;
          if (decoded['service'] != 'voltra-x') continue;
          final candidate = ServerCandidate(
            host: datagram.address.address,
            httpPort: int.tryParse('${decoded['http_port']}') ?? 8086,
            tcpPort: int.tryParse('${decoded['tcp_port']}') ?? 10086,
            name: decoded['name']?.toString() ?? 'Voltra Server',
            version: decoded['version']?.toString() ?? '',
          );
          results[candidate.baseUrl] = candidate;
        } catch (_) {
          // Ignore malformed LAN responses.
        }
      }
    });

    await done.future;
    timer.cancel();
    await sub.cancel();
    socket.close();
    return results.values.toList()
      ..sort((a, b) => a.name.compareTo(b.name));
  }
}
