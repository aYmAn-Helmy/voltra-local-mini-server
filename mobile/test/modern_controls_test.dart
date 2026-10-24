import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voltra_mobile/modern_controls.dart';
import 'package:voltra_mobile/app_controller.dart';
import 'package:voltra_mobile/main.dart';

void main() {
  testWidgets('modern tile triggers only the supplied real control callback',
      (tester) async {
    bool? requested;
    await tester.pumpWidget(MaterialApp(home: Scaffold(
      body: SizedBox(width: 220, height: 240,
        child: ModernOutletTile(
          channel: 1, name: 'Outlet 1',
          on: false, online: true, busy: false, powerW: 0,
          onChanged: (next) => requested = next,
        )),
    )));
    expect(find.text('OFF'), findsOneWidget);
    await tester.tap(find.byType(ModernOutletTile));
    await tester.pump();
    expect(requested, true);
  });

  testWidgets('pending tile is visibly switching and ignores repeated touches',
      (tester) async {
    var commands = 0;
    await tester.pumpWidget(MaterialApp(home: Scaffold(
      body: SizedBox(width: 220, height: 240,
        child: ModernOutletTile(
          channel: 2, name: 'Outlet 2',
          on: true, online: true, busy: true, powerW: 18,
          onChanged: (_) => commands++,
        )),
    )));
    expect(find.text('Switching…'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.tap(find.byType(ModernOutletTile), warnIfMissed: false);
    await tester.pump();
    expect(commands, 0);
  });

  testWidgets('offline tile is disabled and does not send API commands',
      (tester) async {
    var commands = 0;
    await tester.pumpWidget(MaterialApp(home: Scaffold(
      body: SizedBox(width: 220, height: 240,
        child: ModernOutletTile(
          channel: 3, name: 'Outlet 3',
          on: false, online: false, busy: false, powerW: 0,
          onChanged: (_) => commands++,
        )),
    )));
    expect(find.text('Unavailable'), findsOneWidget);
    await tester.tap(find.byType(ModernOutletTile), warnIfMissed: false);
    await tester.pump();
    expect(commands, 0);
  });

  testWidgets('quick navigation, room filtering, and settings actions work',
      (tester) async {
    final controller = AppController();
    controller.overview = {
      'version': '0.22.0',
      'summary': {'total_power_w': 13.2, 'online_strips': 1},
      'strips': [
        {
          'mac': 'D8AA59D28888',
          'name': 'Bedroom Strip',
          'room': 'Bedroom',
          'online': true, 'managed': true, 'state': 'active', 'enabled': true,
          'outlets': [
            for (var i = 1; i <= 4; i++) {'channel': i, 'relay': false}
          ],
        },
      ],
    };
    int? navigate;
    var settings = 0;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: HomePage(
          controller: controller,
          onOpenSettings: () => settings++,
          onNavigate: (tab) => navigate = tab,
        ),
      ),
    ));
    await tester.tap(find.text('Voltra Local').first);
    expect(settings, 1);
    await tester.ensureVisible(find.text('Energy').first);
    await tester.tap(find.text('Energy').first);
    await tester.pump();
    expect(navigate, 1);
    await tester.ensureVisible(find.text('Rooms').first);
    await tester.tap(find.text('Rooms').first);
    await tester.pumpAndSettle();
    expect(find.text('Filter by room'), findsOneWidget);
    expect(find.text('Bedroom'), findsWidgets);
    await tester.tap(find.text('Bedroom').last);
    await tester.pumpAndSettle();
    expect(find.text('Room: Bedroom · Clear'), findsOneWidget);
    controller.dispose();
  });
}
