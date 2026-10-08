import 'package:flutter_test/flutter_test.dart';

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
