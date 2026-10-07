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
}
