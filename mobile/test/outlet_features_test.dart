import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voltra_mobile/voltra_api.dart';

void main() {
  test('Arabic outlet and strip names survive JSON round trip', () async {
    final calls = <http.Request>[];
    final client = MockClient((request) async {
      calls.add(request);
      if (request.method == 'GET') {
        return http.Response(jsonEncode({'name': 'بلايستيشن ٥', 'icon': 'gamepad'}), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
      }
      return http.Response(jsonEncode({'name': 'مشترك غرفة الألعاب'}), 200,
        headers: {'content-type': 'application/json; charset=utf-8'});
    });
    final api = VoltraApi('http://127.0.0.1:8086', client: client);
    expect((await api.getOutletPrefs('D8AA59D28888', 1))['name'], 'بلايستيشن ٥');
    await api.saveOutletPrefs('D8AA59D28888', 1, {'name': 'شاشة التلفزيون'});
    expect(jsonDecode(calls[1].body)['name'], 'شاشة التلفزيون');
    await api.renameStrip('D8AA59D28888', 'مشترك غرفة الألعاب');
    expect(jsonDecode(calls[2].body)['name'], 'مشترك غرفة الألعاب');
    api.close();
  });

  test('Protected power-off includes explicit server confirmation', () async {
    final client = MockClient((request) async {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      expect(payload['on'], false);
      expect(payload['confirm_protected'], true);
      return http.Response(jsonEncode({'metrics': {'last_command_confirmed': true}}), 200,
        headers: {'content-type': 'application/json; charset=utf-8'});
    });
    final api = VoltraApi('http://127.0.0.1:8086', client: client);
    final state = await api.setOutlet('D8AA59D28888', 2, false, confirmProtected: true);
    expect((state['metrics'] as Map)['last_command_confirmed'], true);
    api.close();
  });

  test('Activity and automation use real API endpoints', () async {
    final paths = <String>[];
    final client = MockClient((request) async {
      paths.add(request.url.path);
      return http.Response(jsonEncode({'events': [], 'schedules': {}}), 200);
    });
    final api = VoltraApi('http://127.0.0.1:8086', client: client);
    await api.outletActivity('D8AA59D28888', 4);
    await api.auditFeed();
    await api.createScene('وضع الألعاب', 'D8AA59D28888', 4, true);
    expect(paths, [
      '/voltra/api/strips/D8AA59D28888/outlets/4/activity',
      '/voltra/api/audit',
      '/voltra/api/scenes',
    ]);
    api.close();
  });
}
