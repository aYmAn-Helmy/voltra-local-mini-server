import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:voltra_mobile/voltra_api.dart';

void main() {
  test('server candidate exposes LAN base URL', () {
    const server = ServerCandidate(
      host: '192.168.1.65',
      httpPort: 8086,
      tcpPort: 10086,
      name: 'Voltra Server',
      version: '0.20.0',
    );

    expect(server.baseUrl, 'http://192.168.1.65:8086');
  });

  test('Miqaat local URLs work without tokens and remote addresses are rejected', () {
    final api = VoltraApi('192.168.1.45:8086', client: MockClient(
      (_) async => http.Response('{}', 200),
    ));
    expect(api.baseUrl, 'http://192.168.1.45:8086');
    expect(VoltraApi.isLocalHost('10.0.0.10'), true);
    expect(VoltraApi.isLocalHost('172.31.1.10'), true);
    expect(VoltraApi.isLocalHost('voltra.local'), true);
    expect(VoltraApi.isLocalHost('8.8.8.8'), false);
    expect(VoltraApi.isLocalHost('203.0.113.40'), false);
    expect(
      () => VoltraApi('https://public.example.com', client: MockClient(
        (_) async => http.Response('{}', 200),
      )),
      throwsA(isA<VoltraException>()),
    );
    expect(
      () => VoltraApi('http://192.168.1.45:8086/malicious/path', client: MockClient(
        (_) async => http.Response('{}', 200),
      )),
      throwsA(isA<VoltraException>()),
    );
    api.close();
  });

  test('Miqaat GET and outlet POST never include Authorization headers', () async {
    var calls = 0;
    final client = MockClient((request) async {
      calls++;
      expect(request.headers.keys.any((key) => key.toLowerCase() == 'authorization'), false);
      expect(request.url.host, '192.168.1.45');
      if (request.method == 'POST') {
        expect(jsonDecode(request.body), {'on': true});
        return http.Response(jsonEncode({'metrics': {'last_command_confirmed': true}}), 200);
      }
      return http.Response(jsonEncode({'status': 'ok'}), 200);
    });
    final api = VoltraApi('http://192.168.1.45:8086', client: client);
    await api.health();
    await api.setOutlet('D8AA59D28888', 1, true);
    expect(calls, 2);
    api.close();
  });

  test('direct provisioning validates setup fields before opening a socket', () async {
    expect(
      VoltraApi.provisionDirect(
        ssid: 'bad:ssid',
        password: 'password',
        serverIp: '192.168.1.45',
      ),
      throwsA(isA<VoltraException>()),
    );

    expect(
      VoltraApi.provisionDirect(
        ssid: 'Home WiFi',
        password: 'password',
        serverIp: 'not-an-ip',
      ),
      throwsA(isA<VoltraException>()),
    );
  });

}
