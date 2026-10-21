import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voltra_mobile/app_controller.dart';
import 'package:voltra_mobile/voltra_api.dart';

const mac = 'D8AA59D28888';

Map<String, dynamic> state(bool relay) => {
      'strips': [
        {
          'mac': mac,
          'name': 'Test Strip',
          'online': true,
          'managed': true,
          'enabled': true,
          'state': 'active',
          'outlets': [
            for (var i = 1; i <= 4; i++)
              {'channel': i, 'relay': relay},
          ],
        }
      ],
      'summary': {'total_power_w': 0, 'online_strips': 1},
      'version': '0.21.0',
    };

bool channelOn(AppController ctrl, int channel) {
  final strips = ctrl.strips;
  final outlets = strips.single['outlets'] as List<dynamic>;
  return (outlets[channel - 1] as Map<String, dynamic>)['relay'] == true;
}

void main() {
  test('optimistic outlet updates immediately then verifies API reply', () async {
    final sent = Completer<void>();
    final proceed = Completer<void>();
    var requests = 0;
    final client = MockClient((request) async {
      requests++;
      if (request.method == 'POST') {
        sent.complete();
        await proceed.future;
        return http.Response(jsonEncode({'metrics': {'last_command_confirmed': true}}), 200);
      }
      if (request.url.path.endsWith('/overview')) {
        return http.Response(jsonEncode(state(true)), 200);
      }
      return http.Response(jsonEncode({'schedules': {}, 'rules': {}, 'queue': []}), 200);
    });
    final ctrl = AppController();
    ctrl.api = VoltraApi('http://127.0.0.1:8086', client: client);
    ctrl.overview = state(false);
    final change = ctrl.setOutlet(mac, 1, true);
    await sent.future;
    expect(channelOn(ctrl, 1), true);
    expect(ctrl.outletBusy(mac, 1), true);
    proceed.complete();
    await change;
    expect(ctrl.outletBusy(mac, 1), false);
    expect(channelOn(ctrl, 1), true);
    expect(requests, 3); // command + one overview + one automation
    ctrl.dispose();
  });

  test('failed command clears pending state and refreshes real outlet', () async {
    final client = MockClient((request) async {
      if (request.method == 'POST') {
        return http.Response(jsonEncode({'error': 'relay unavailable'}), 504);
      }
      if (request.url.path.endsWith('/overview')) {
        return http.Response(jsonEncode(state(false)), 200);
      }
      return http.Response(jsonEncode({'schedules': {}, 'rules': {}, 'queue': []}), 200);
    });
    final ctrl = AppController();
    ctrl.api = VoltraApi('http://127.0.0.1:8086', client: client);
    ctrl.overview = state(false);
    await expectLater(ctrl.setOutlet(mac, 1, true), throwsA(isA<VoltraException>()));
    expect(ctrl.outletBusy(mac, 1), false);
    expect(channelOn(ctrl, 1), false);
    ctrl.dispose();
  });

  test('bulk control sends four commands but refreshes once', () async {
    var commands = 0;
    var overviewCalls = 0;
    var automationCalls = 0;
    final client = MockClient((request) async {
      if (request.method == 'POST') {
        commands++;
        return http.Response(jsonEncode({'metrics': {'last_command_confirmed': true}}), 200);
      }
      if (request.url.path.endsWith('/overview')) {
        overviewCalls++;
        return http.Response(jsonEncode(state(true)), 200);
      }
      automationCalls++;
      return http.Response(jsonEncode({'schedules': {}, 'rules': {}, 'queue': []}), 200);
    });
    final ctrl = AppController();
    ctrl.api = VoltraApi('http://127.0.0.1:8086', client: client);
    ctrl.overview = state(false);
    await ctrl.setAll(ctrl.strips.single, true);
    expect(commands, 4);
    expect(overviewCalls, 1);
    expect(automationCalls, 1);
    expect(ctrl.busyOutlets, isEmpty);
    expect(channelOn(ctrl, 1), true);
    ctrl.dispose();
  });
  test('Android safety settings are saved by a real PUT and refreshed', () async {
    var updates = 0;
    final client = MockClient((request) async {
      if (request.method == 'PUT' && request.url.path == '/voltra/api/settings') {
        updates++;
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['alert_auto_off_enabled'], false);
        expect(body['alert_max_total_current_a'], 12.0);
        return http.Response(jsonEncode(body), 200);
      }
      if (request.url.path.endsWith('/overview')) {
        return http.Response(jsonEncode({
          ...state(false),
          'settings': {
            'alert_max_total_current_a': 12,
            'alert_auto_off_enabled': false,
          },
        }), 200);
      }
      return http.Response(jsonEncode({'schedules': {}, 'rules': {}, 'queue': []}), 200);
    });
    final ctrl = AppController();
    ctrl.api = VoltraApi('http://127.0.0.1:8086', client: client);
    await ctrl.updateSafetySettings({
      'alert_max_total_current_a': 12.0,
      'alert_max_total_power_w': 3000.0,
      'alert_max_temperature_c': 75.0,
      'alert_auto_off_enabled': false,
    });
    expect(updates, 1);
    expect(ctrl.overview?['settings']['alert_max_total_current_a'], 12);
    ctrl.dispose();
  });

}
