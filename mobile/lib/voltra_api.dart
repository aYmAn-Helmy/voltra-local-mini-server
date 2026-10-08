import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cronet_http/cronet_http.dart';
import 'package:http/http.dart' as http;

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
      final engine = CronetEngine.build(
        cacheMode: CacheMode.disabled,
        enableHttp2: false,
        enableQuic: false,
        userAgent: 'Voltra-Mobile/1.3.1',
      );
      return CronetClient.fromCronetEngine(engine, closeEngine: true);
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
