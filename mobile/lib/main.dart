import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'app_controller.dart';
import 'security_controller.dart';
import 'voltra_api.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VoltraMobileApp());
}

class VoltraMobileApp extends StatefulWidget {
  const VoltraMobileApp({super.key});

  @override
  State<VoltraMobileApp> createState() => _VoltraMobileAppState();
}

class _VoltraMobileAppState extends State<VoltraMobileApp>
    with WidgetsBindingObserver {
  final controller = AppController();
  final security = SecurityController();
  bool booting = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.wait([
      controller.initialize(),
      security.initialize(),
    ]).whenComplete(() {
      if (mounted) setState(() => booting = false);
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.paused:
      case AppLifecycleState.hidden:
        security.markBackgrounded();
        break;
      case AppLifecycleState.resumed:
        security.handleResumed();
        break;
      case AppLifecycleState.inactive:
      case AppLifecycleState.detached:
        break;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    controller.dispose();
    security.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const green = Color(0xFF39E27D);
    const bg = Color(0xFF070C16);
    const surface = Color(0xFF111A2B);

    final scheme = ColorScheme.fromSeed(
      seedColor: green,
      brightness: Brightness.dark,
      surface: surface,
    ).copyWith(
      primary: green,
      onPrimary: const Color(0xFF062014),
      surface: surface,
      outline: const Color(0xFF263249),
      error: const Color(0xFFFF7380),
    );

    return MaterialApp(
      title: 'Voltra',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: scheme,
        scaffoldBackgroundColor: bg,
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          backgroundColor: bg,
          elevation: 0,
          scrolledUnderElevation: 0,
        ),
        cardTheme: CardThemeData(
          color: surface,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
            side: const BorderSide(color: Color(0xFF202B3E)),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF101827),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: Color(0xFF263249)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: Color(0xFF263249)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: green),
          ),
        ),
        navigationBarTheme: const NavigationBarThemeData(
          backgroundColor: Color(0xF20C1320),
          indicatorColor: Color(0xFF133127),
          labelTextStyle: WidgetStatePropertyAll(
            TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ),
      ),
      home: booting
          ? const _BootScreen()
          : AnimatedBuilder(
              animation: security,
              builder: (context, _) {
                if (security.enabled && !security.unlocked) {
                  return LockScreen(security: security);
                }
                return AnimatedBuilder(
                  animation: controller,
                  builder: (context, _) {
                    if (!controller.connected) {
                      return SetupScreen(controller: controller);
                    }
                    return MainShell(
                      controller: controller,
                      security: security,
                    );
                  },
                );
              },
            ),
    );
  }
}

class _BootScreen extends StatelessWidget {
  const _BootScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _LogoMark(size: 72),
            SizedBox(height: 22),
            CircularProgressIndicator(strokeWidth: 2),
            SizedBox(height: 14),
            Text(
              'Starting Voltra',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            SizedBox(height: 5),
            Text(
              'Connecting to your local server…',
              style: TextStyle(color: Color(0xFF7D879B), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _LogoMark extends StatelessWidget {
  final double size;
  const _LogoMark({this.size = 54});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primary,
        borderRadius: BorderRadius.circular(size * .28),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).colorScheme.primary.withValues(alpha: .22),
            blurRadius: 30,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Icon(
        Icons.bolt_rounded,
        size: size * .56,
        color: Theme.of(context).colorScheme.onPrimary,
      ),
    );
  }
}

class SetupScreen extends StatefulWidget {
  final AppController controller;
  const SetupScreen({super.key, required this.controller});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final manual = TextEditingController();
  List<ServerCandidate> found = [];
  bool scanning = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(scan);
  }

  @override
  void dispose() {
    manual.dispose();
    super.dispose();
  }

  Future<void> scan() async {
    setState(() => scanning = true);
    try {
      final result = await VoltraApi.discover();
      if (mounted) setState(() => found = result);
    } catch (e) {
      if (mounted) _toast(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => scanning = false);
    }
  }

  void _toast(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor:
            error ? const Color(0xFF4A1F29) : const Color(0xFF153425),
      ),
    );
  }

  Future<void> connect(String url) async {
    await widget.controller.connect(url);
    if (widget.controller.error != null && mounted) {
      _toast(widget.controller.error!, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 34, 22, 30),
          children: [
            const Align(
              alignment: Alignment.centerLeft,
              child: _LogoMark(size: 64),
            ),
            const SizedBox(height: 28),
            const Text(
              'Your power.\nYour network.',
              style: TextStyle(
                fontSize: 35,
                height: 1.02,
                fontWeight: FontWeight.w900,
                letterSpacing: -1.5,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Voltra controls your smart power strips directly over your LAN. No cloud account required.',
              style: TextStyle(
                color: Color(0xFF8993A7),
                fontSize: 13,
                height: 1.55,
              ),
            ),
            const SizedBox(height: 30),
            _SectionTitle(
              eyebrow: 'AUTO DISCOVERY',
              title: scanning ? 'Looking for Voltra…' : 'Servers on this network',
              trailing: IconButton(
                onPressed: scanning ? null : scan,
                icon: scanning
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh_rounded),
              ),
            ),
            const SizedBox(height: 10),
            if (found.isEmpty && !scanning)
              const _EmptyCard(
                icon: Icons.wifi_find_rounded,
                title: 'No server found',
                text:
                    'Make sure your phone and Voltra server are on the same LAN, or enter the server IP below.',
              ),
            ...found.map(
              (server) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _ServerCard(
                  server: server,
                  busy: widget.controller.loading,
                  onTap: () => connect(server.baseUrl),
                ),
              ),
            ),
            const SizedBox(height: 18),
            const _SectionTitle(
              eyebrow: 'MANUAL',
              title: 'Connect by IP',
            ),
            const SizedBox(height: 10),
            TextField(
              controller: manual,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.dns_rounded),
                hintText: '192.168.1.65:8086',
                labelText: 'Voltra server',
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: widget.controller.loading
                  ? null
                  : () {
                      if (manual.text.trim().isNotEmpty) {
                        connect(manual.text.trim());
                      }
                    },
              icon: const Icon(Icons.arrow_forward_rounded),
              label: const Text('Connect to Voltra'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(15),
                ),
              ),
            ),
            const SizedBox(height: 18),
            const _InfoRow(
              icon: Icons.shield_outlined,
              title: 'Local-first',
              text: 'Strip commands stay on your network.',
            ),
            const _InfoRow(
              icon: Icons.cloud_off_outlined,
              title: 'Works without Internet',
              text: 'The local server remains in control when WAN is down.',
            ),
          ],
        ),
      ),
    );
  }
}

class _ServerCard extends StatelessWidget {
  final ServerCandidate server;
  final bool busy;
  final VoidCallback onTap;
  const _ServerCard({
    required this.server,
    required this.busy,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: busy ? null : onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: const Color(0xFF123128),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(
                  Icons.router_rounded,
                  color: Color(0xFF39E27D),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      server.name,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${server.host}:${server.httpPort} · v${server.version}',
                      style: const TextStyle(
                        color: Color(0xFF7E899E),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  final AppController controller;
  final SecurityController security;
  const MainShell({
    super.key,
    required this.controller,
    required this.security,
  });

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int index = 0;

  String get title => switch (index) {
        0 => 'My strips',
        1 => 'Consumption',
        2 => 'Automation',
        _ => 'Settings',
      };

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomePage(controller: widget.controller),
      EnergyPage(controller: widget.controller),
      AutomationPage(controller: widget.controller),
      SettingsPage(
        controller: widget.controller,
        security: widget.security,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 18,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _PulseDot(),
                SizedBox(width: 7),
                Text(
                  'VOLTRA LIVE',
                  style: TextStyle(
                    color: Color(0xFF39E27D),
                    fontSize: 9,
                    letterSpacing: 2.1,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: const TextStyle(
                fontSize: 27,
                fontWeight: FontWeight.w900,
                letterSpacing: -1,
              ),
            ),
          ],
        ),
        toolbarHeight: 78,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed:
                widget.controller.loading ? null : widget.controller.refresh,
            icon: widget.controller.loading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: IndexedStack(index: index, children: pages),
      floatingActionButton: index == 0
          ? FloatingActionButton.extended(
              onPressed: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) =>
                        AddStripPage(controller: widget.controller),
                  ),
                );
                await widget.controller.refresh(silent: true);
              },
              icon: const Icon(Icons.add_rounded),
              label: const Text('Add strip'),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.power_rounded),
            label: 'Strips',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_rounded),
            label: 'Energy',
          ),
          NavigationDestination(
            icon: Icon(Icons.schedule_rounded),
            label: 'Automation',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_rounded),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  final AppController controller;
  const HomePage({super.key, required this.controller});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final strips = controller.activeStrips;
    final filtered = strips.where((strip) {
      if (query.trim().isEmpty) return true;
      final q = query.toLowerCase();
      return [
        strip['name'],
        strip['mac'],
        strip['room'],
      ].join(' ').toLowerCase().contains(q);
    }).toList();

    final totalPower =
        _num(controller.summary['total_power_w']).toStringAsFixed(1);
    final online = controller.summary['online_strips'] ?? 0;
    var outletTotal = 0;
    var outletOn = 0;
    for (final strip in strips) {
      final outlets = strip['outlets'];
      if (outlets is List) {
        outletTotal += 4;
        outletOn += outlets.where((o) => o is Map && o['relay'] == true).length;
      }
    }
    final schedules =
        (controller.automation['schedules'] as Map?)?.length ?? 0;

    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 110),
        children: [
          Card(
            child: InkWell(
              onTap: () {},
              borderRadius: BorderRadius.circular(22),
              child: Padding(
                padding: const EdgeInsets.all(13),
                child: Row(
                  children: [
                    const _LogoMark(size: 44),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Voltra Local',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            'v${controller.version} · ${controller.baseUrl}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Color(0xFF808A9E),
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(
                      Icons.chevron_right_rounded,
                      color: Color(0xFF747F93),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PowerHero(
            watts: totalPower,
            online: '$online',
            outlets: '$outletOn/$outletTotal',
            plans: '$schedules',
          ),
          const SizedBox(height: 14),
          const _QuickGrid(),
          const SizedBox(height: 14),
          TextField(
            onChanged: (value) => setState(() => query = value),
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search_rounded),
              hintText: 'Search strips and outlets',
            ),
          ),
          const SizedBox(height: 20),
          _SectionTitle(
            eyebrow: 'LIVE DEVICES',
            title: query.isEmpty ? 'Your strips' : 'Search results',
            trailing: _CountBadge(value: filtered.length),
          ),
          const SizedBox(height: 10),
          if (filtered.isEmpty)
            _EmptyCard(
              icon: query.isEmpty
                  ? Icons.power_off_rounded
                  : Icons.search_off_rounded,
              title: query.isEmpty ? 'No strips yet' : 'No matching strips',
              text: query.isEmpty
                  ? 'Tap Add strip to adopt a discovered MTTL-W01.'
                  : 'Try the strip name, room, or MAC address.',
            ),
          ...filtered.map(
            (strip) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: StripCard(
                controller: controller,
                strip: strip,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PowerHero extends StatelessWidget {
  final String watts;
  final String online;
  final String outlets;
  final String plans;
  const _PowerHero({
    required this.watts,
    required this.online,
    required this.outlets,
    required this.plans,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 17),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF162136), Color(0xFF101827)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFF243047)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Total power right now',
            style: TextStyle(color: Color(0xFF9099AD), fontSize: 12),
          ),
          const SizedBox(height: 7),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                watts,
                style: const TextStyle(
                  color: Color(0xFF39E27D),
                  fontSize: 46,
                  height: 1,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -2,
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(left: 8, bottom: 6),
                child: Text(
                  'W',
                  style: TextStyle(
                    color: Color(0xFF97A1B5),
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 15,
            runSpacing: 7,
            children: [
              _MiniMetric(value: online, label: 'strips online'),
              _MiniMetric(value: outlets, label: 'outlets on'),
              _MiniMetric(value: plans, label: 'plans active'),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickGrid extends StatelessWidget {
  const _QuickGrid();

  @override
  Widget build(BuildContext context) {
    final items = [
      (Icons.bar_chart_rounded, 'Consumption'),
      (Icons.schedule_rounded, 'Schedules'),
      (Icons.bolt_rounded, 'Power automation'),
      (Icons.meeting_room_outlined, 'Rooms'),
    ];
    return Row(
      children: [
        for (var i = 0; i < items.length; i++) ...[
          if (i > 0) const SizedBox(width: 7),
          Expanded(
            child: Container(
              height: 82,
              padding: const EdgeInsets.symmetric(horizontal: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF101827),
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: const Color(0xFF222D42)),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: const Color(0xFF123128),
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: Icon(
                      items[i].$1,
                      color: const Color(0xFF39E27D),
                      size: 19,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    items[i].$2,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF8B95A9),
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class StripCard extends StatelessWidget {
  final AppController controller;
  final Map<String, dynamic> strip;
  const StripCard({
    super.key,
    required this.controller,
    required this.strip,
  });

  List<Map<String, dynamic>> get outlets {
    final raw = strip['outlets'];
    if (raw is! List) return [];
    return raw
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Map<String, dynamic>? outlet(int channel) {
    for (final item in outlets) {
      if (int.tryParse('${item['channel']}') == channel) return item;
    }
    return null;
  }

  Future<void> _toggle(
    BuildContext context,
    int channel,
    bool on,
  ) async {
    try {
      await controller.setOutlet(
        strip['mac']?.toString() ?? '',
        channel,
        on,
      );
    } catch (e) {
      if (context.mounted) _snack(context, e.toString(), error: true);
    }
  }

  Future<void> _setAll(BuildContext context, bool on) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(on ? 'Turn all outlets on?' : 'Turn all outlets off?'),
        content: Text(
          '${strip['name'] ?? 'This strip'} will switch all four outlets ${on ? 'on' : 'off'}.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(on ? 'Turn all on' : 'Turn all off'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await controller.setAll(strip, on);
    } catch (e) {
      if (context.mounted) _snack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final online = strip['online'] == true;
    final enabled = strip['enabled'] != false && strip['state'] == 'active';
    final status = strip['state'] == 'disabled'
        ? 'DISABLED'
        : online
            ? 'ONLINE'
            : 'OFFLINE';
    final health = strip['health'] is Map
        ? (strip['health'] as Map)['status']?.toString() ?? 'unknown'
        : 'unknown';

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 15, 14, 13),
        child: Column(
          children: [
            Row(
              children: [
                _PulseDot(active: online),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    strip['name']?.toString() ?? strip['mac']?.toString() ?? '',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 18,
                    ),
                  ),
                ),
                _StatusPill(text: status, active: online),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${strip['room']?.toString().trim().isNotEmpty == true ? strip['room'] : 'Local strip'} · $health',
                    style: const TextStyle(
                      color: Color(0xFF818BA0),
                      fontSize: 10,
                    ),
                  ),
                ),
                Text(
                  '${_num(strip['total_power_w']).toStringAsFixed(1)} W',
                  style: const TextStyle(
                    color: Color(0xFF39E27D),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 13),
            GridView.count(
              crossAxisCount: 2,
              physics: const NeverScrollableScrollPhysics(),
              shrinkWrap: true,
              crossAxisSpacing: 9,
              mainAxisSpacing: 9,
              childAspectRatio: 1.38,
              children: [
                for (var channel = 1; channel <= 4; channel++)
                  _OutletTile(
                    channel: channel,
                    data: outlet(channel),
                    enabled: online && enabled,
                    onToggle: (value) => _toggle(context, channel, value),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed:
                        online && enabled ? () => _setAll(context, true) : null,
                    icon: const Icon(Icons.power_rounded, size: 17),
                    label: const Text('Turn all on'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF39E27D),
                      side: const BorderSide(color: Color(0xFF28734F)),
                      minimumSize: const Size.fromHeight(44),
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed:
                        online && enabled ? () => _setAll(context, false) : null,
                    icon: const Icon(Icons.power_off_rounded, size: 17),
                    label: const Text('Turn all off'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(44),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _OutletTile extends StatelessWidget {
  final int channel;
  final Map<String, dynamic>? data;
  final bool enabled;
  final ValueChanged<bool> onToggle;
  const _OutletTile({
    required this.channel,
    required this.data,
    required this.enabled,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final on = data?['relay'] == true;
    final power = _num(data?['power_w']);
    return Material(
      color: on ? const Color(0xFF15332D) : const Color(0xFF151E30),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(15),
        side: BorderSide(
          color:
              on ? const Color(0xFF28734F) : const Color(0xFF232E43),
        ),
      ),
      child: InkWell(
        onTap: enabled ? () => onToggle(!on) : null,
        borderRadius: BorderRadius.circular(15),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color:
                        on ? const Color(0xFF39E27D) : const Color(0xFF3A455B),
                    width: 2,
                  ),
                ),
                child: Icon(
                  Icons.power_rounded,
                  size: 17,
                  color:
                      on ? const Color(0xFF39E27D) : const Color(0xFF657087),
                ),
              ),
              const Spacer(),
              Text(
                'Outlet $channel',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                on ? 'ON · ${power.toStringAsFixed(1)} W' : 'OFF',
                style: TextStyle(
                  color:
                      on ? const Color(0xFF39E27D) : const Color(0xFF737D92),
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class EnergyPage extends StatefulWidget {
  final AppController controller;
  const EnergyPage({super.key, required this.controller});

  @override
  State<EnergyPage> createState() => _EnergyPageState();
}

class _EnergyPageState extends State<EnergyPage> {
  String? mac;
  double hours = 24;
  int? outlet;
  Future<Map<String, dynamic>>? future;

  @override
  void initState() {
    super.initState();
    Future.microtask(_ensure);
  }

  void _ensure() {
    final strips = widget.controller.activeStrips;
    if (strips.isEmpty) return;
    mac ??= strips.first['mac']?.toString();
    _load();
  }

  void _load() {
    if (mac == null) return;
    setState(() {
      future = widget.controller.energy(mac!, hours, outlet: outlet);
    });
  }

  @override
  Widget build(BuildContext context) {
    final strips = widget.controller.activeStrips;
    if (strips.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: _EmptyCard(
          icon: Icons.bar_chart_rounded,
          title: 'No energy data yet',
          text: 'Add a strip first, then Voltra will start collecting telemetry.',
        ),
      );
    }
    mac ??= strips.first['mac']?.toString();
    future ??= widget.controller.energy(mac!, hours, outlet: outlet);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      children: [
        const _SectionTitle(
          eyebrow: 'ENERGY INSIGHTS',
          title: 'Consumption',
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                DropdownButtonFormField<String>(
                  initialValue: mac,
                  decoration: const InputDecoration(labelText: 'Strip'),
                  items: strips
                      .map(
                        (s) => DropdownMenuItem(
                          value: s['mac']?.toString(),
                          child: Text(s['name']?.toString() ?? 'Strip'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    mac = value;
                    _load();
                  },
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<double>(
                        initialValue: hours,
                        decoration: const InputDecoration(labelText: 'Period'),
                        items: const [
                          DropdownMenuItem(value: 6, child: Text('6 hours')),
                          DropdownMenuItem(value: 24, child: Text('24 hours')),
                          DropdownMenuItem(value: 168, child: Text('7 days')),
                          DropdownMenuItem(value: 720, child: Text('30 days')),
                        ],
                        onChanged: (value) {
                          hours = value ?? 24;
                          _load();
                        },
                      ),
                    ),
                    const SizedBox(width: 9),
                    Expanded(
                      child: DropdownButtonFormField<int?>(
                        initialValue: outlet,
                        decoration: const InputDecoration(labelText: 'Scope'),
                        items: const [
                          DropdownMenuItem<int?>(
                            value: null,
                            child: Text('Whole strip'),
                          ),
                          DropdownMenuItem(value: 1, child: Text('Outlet 1')),
                          DropdownMenuItem(value: 2, child: Text('Outlet 2')),
                          DropdownMenuItem(value: 3, child: Text('Outlet 3')),
                          DropdownMenuItem(value: 4, child: Text('Outlet 4')),
                        ],
                        onChanged: (value) {
                          outlet = value;
                          _load();
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        FutureBuilder<Map<String, dynamic>>(
          future: future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Padding(
                padding: EdgeInsets.all(40),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError) {
              return _EmptyCard(
                icon: Icons.error_outline_rounded,
                title: 'Could not load telemetry',
                text: snapshot.error.toString(),
              );
            }
            final bundle = snapshot.data ?? {};
            final summary =
                Map<String, dynamic>.from(bundle['summary'] as Map? ?? {});
            final history =
                Map<String, dynamic>.from(bundle['history'] as Map? ?? {});
            final points = (history['points'] as List? ?? const [])
                .whereType<Map>()
                .map((e) => Map<String, dynamic>.from(e))
                .toList();
            final price =
                _num((widget.controller.overview?['settings'] as Map?)?[
                    'energy_price_per_kwh']);
            final currency =
                (widget.controller.overview?['settings'] as Map?)?['currency']
                        ?.toString() ??
                    'EGP';
            final energy = _num(summary['energy_kwh']);
            return Column(
              children: [
                GridView.count(
                  crossAxisCount: 2,
                  physics: const NeverScrollableScrollPhysics(),
                  shrinkWrap: true,
                  crossAxisSpacing: 9,
                  mainAxisSpacing: 9,
                  childAspectRatio: 1.55,
                  children: [
                    _MetricCard(
                      label: 'Average power',
                      value:
                          '${_num(summary['average_power_w']).toStringAsFixed(1)} W',
                      icon: Icons.show_chart_rounded,
                    ),
                    _MetricCard(
                      label: 'Peak power',
                      value:
                          '${_num(summary['max_power_w']).toStringAsFixed(1)} W',
                      icon: Icons.bolt_rounded,
                    ),
                    _MetricCard(
                      label: 'Energy',
                      value: '${energy.toStringAsFixed(3)} kWh',
                      icon: Icons.electric_meter_rounded,
                      accent: true,
                    ),
                    _MetricCard(
                      label: 'Estimated cost',
                      value:
                          '${(energy * price).toStringAsFixed(2)} $currency',
                      icon: Icons.payments_outlined,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(15),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const _SectionTitle(
                          eyebrow: 'POWER HISTORY',
                          title: 'Live telemetry',
                        ),
                        const SizedBox(height: 14),
                        SizedBox(
                          height: 220,
                          child: points.isEmpty
                              ? const Center(
                                  child: Text(
                                    'No samples in this period.',
                                    style: TextStyle(
                                      color: Color(0xFF7D879C),
                                    ),
                                  ),
                                )
                              : CustomPaint(
                                  painter: _PowerChartPainter(points),
                                  size: Size.infinite,
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _PowerChartPainter extends CustomPainter {
  final List<Map<String, dynamic>> points;
  _PowerChartPainter(this.points);

  @override
  void paint(Canvas canvas, Size size) {
    final values = points.map((p) => _num(p['power_w'])).toList();
    if (values.isEmpty) return;
    final maxValue = math.max(1.0, values.reduce(math.max));
    const pad = 10.0;

    final gridPaint = Paint()
      ..color = const Color(0xFF263249)
      ..strokeWidth = 1;
    for (var i = 1; i <= 3; i++) {
      final y = pad + (size.height - pad * 2) * i / 4;
      canvas.drawLine(
        Offset(pad, y),
        Offset(size.width - pad, y),
        gridPaint,
      );
    }

    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final x = pad +
          (values.length == 1
              ? 0
              : i / (values.length - 1) * (size.width - pad * 2));
      final y = size.height -
          pad -
          (values[i] / maxValue) * (size.height - pad * 2);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final glow = Paint()
      ..color = const Color(0x3339E27D)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(path, glow);

    final line = Paint()
      ..color = const Color(0xFF39E27D)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(path, line);
  }

  @override
  bool shouldRepaint(covariant _PowerChartPainter oldDelegate) =>
      oldDelegate.points != points;
}

class AutomationPage extends StatelessWidget {
  final AppController controller;
  const AutomationPage({super.key, required this.controller});

  List<Map<String, dynamic>> get schedules {
    final raw = controller.automation['schedules'];
    if (raw is! Map) return [];
    return raw.values
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList()
      ..sort(
        (a, b) => (b['created_at']?.toString() ?? '')
            .compareTo(a['created_at']?.toString() ?? ''),
      );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      children: [
        const _SectionTitle(
          eyebrow: 'LOCAL AUTOMATION',
          title: 'Schedules & timers',
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _ActionCard(
                icon: Icons.schedule_rounded,
                title: 'Schedule',
                subtitle: 'Daily / weekly',
                onTap: () => _showScheduleSheet(context, controller),
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: _ActionCard(
                icon: Icons.timer_outlined,
                title: 'Countdown',
                subtitle: '15m to 2h',
                onTap: () => _showCountdownSheet(context, controller),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        const _SectionTitle(
          eyebrow: 'ACTIVE PLANS',
          title: 'Schedules',
        ),
        const SizedBox(height: 9),
        if (schedules.isEmpty)
          const _EmptyCard(
            icon: Icons.schedule_rounded,
            title: 'No schedules yet',
            text: 'Create a schedule or countdown for any outlet.',
          ),
        ...schedules.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              margin: EdgeInsets.zero,
              child: ListTile(
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: const Color(0xFF123128),
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: const Icon(
                    Icons.schedule_rounded,
                    color: Color(0xFF39E27D),
                  ),
                ),
                title: Text(
                  'Outlet ${item['outlet'] ?? '—'} · ${item['on'] == true ? 'Turn on' : 'Turn off'}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                subtitle: Text(
                  item['run_at']?.toString() ??
                      '${item['time'] ?? '—'} · ${(item['days'] as List?)?.length ?? 0} days',
                  style: const TextStyle(fontSize: 10),
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline_rounded),
                  onPressed: () async {
                    try {
                      await controller
                          .deleteSchedule(item['id']?.toString() ?? '');
                    } catch (e) {
                      if (context.mounted) {
                        _snack(context, e.toString(), error: true);
                      }
                    }
                  },
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 18),
        const _SectionTitle(
          eyebrow: 'ONE TAP',
          title: 'Scenes',
        ),
        const SizedBox(height: 9),
        if (controller.scenes.isEmpty)
          const _EmptyCard(
            icon: Icons.auto_awesome_rounded,
            title: 'No scenes',
            text: 'Create scenes from the Voltra web dashboard, then run them here.',
          ),
        Wrap(
          spacing: 9,
          runSpacing: 9,
          children: controller.scenes
              .map(
                (scene) => SizedBox(
                  width: (MediaQuery.sizeOf(context).width - 41) / 2,
                  child: _ActionCard(
                    icon: Icons.play_arrow_rounded,
                    title: scene['name']?.toString() ?? 'Scene',
                    subtitle:
                        '${(scene['actions'] as List?)?.length ?? 0} actions',
                    onTap: () async {
                      try {
                        await controller
                            .runScene(scene['id']?.toString() ?? '');
                        if (context.mounted) {
                          _snack(context, 'Scene executed.');
                        }
                      } catch (e) {
                        if (context.mounted) {
                          _snack(context, e.toString(), error: true);
                        }
                      }
                    },
                  ),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

Future<void> _showScheduleSheet(
  BuildContext context,
  AppController controller,
) async {
  final targets = _targets(controller);
  if (targets.isEmpty) {
    _snack(context, 'No controllable outlets available.', error: true);
    return;
  }
  String target = targets.first.$1;
  var on = false;
  var time = const TimeOfDay(hour: 23, minute: 0);
  final days = <int>{0, 1, 2, 3, 4, 5, 6};

  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: const Color(0xFF0F1726),
    builder: (sheetContext) => StatefulBuilder(
      builder: (sheetContext, setLocal) {
        final labels = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
        return Padding(
          padding: EdgeInsets.fromLTRB(
            18,
            18,
            18,
            18 + MediaQuery.viewInsetsOf(sheetContext).bottom,
          ),
          child: ListView(
            shrinkWrap: true,
            children: [
              const _SectionTitle(
                eyebrow: 'NEW PLAN',
                title: 'Schedule an outlet',
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: target,
                decoration: const InputDecoration(labelText: 'Target outlet'),
                items: targets
                    .map(
                      (t) => DropdownMenuItem(
                        value: t.$1,
                        child: Text(t.$2),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setLocal(() => target = value ?? target),
              ),
              const SizedBox(height: 10),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Time'),
                subtitle: Text(time.format(sheetContext)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () async {
                  final picked = await showTimePicker(
                    context: sheetContext,
                    initialTime: time,
                  );
                  if (picked != null) setLocal(() => time = picked);
                },
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: on,
                title: Text(on ? 'Turn outlet on' : 'Turn outlet off'),
                onChanged: (value) => setLocal(() => on = value),
              ),
              const SizedBox(height: 6),
              const Text(
                'Days',
                style: TextStyle(
                  color: Color(0xFF8791A5),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  for (var i = 0; i < 7; i++) ...[
                    if (i > 0) const SizedBox(width: 5),
                    Expanded(
                      child: FilterChip(
                        selected: days.contains(i),
                        label: Text(labels[i]),
                        onSelected: (selected) {
                          setLocal(() {
                            selected ? days.add(i) : days.remove(i);
                          });
                        },
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: days.isEmpty
                    ? null
                    : () async {
                        final parsed = _parseTarget(target);
                        try {
                          await controller.createSchedule({
                            'mac': parsed.$1,
                            'outlet': parsed.$2,
                            'on': on,
                            'time':
                                '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
                            'days': days.toList()..sort(),
                            'offline_policy': 'queue',
                          });
                          if (sheetContext.mounted) {
                            Navigator.pop(sheetContext);
                          }
                        } catch (e) {
                          if (sheetContext.mounted) {
                            _snack(sheetContext, e.toString(), error: true);
                          }
                        }
                      },
                icon: const Icon(Icons.schedule_rounded),
                label: const Text('Create schedule'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}

Future<void> _showCountdownSheet(
  BuildContext context,
  AppController controller,
) async {
  final targets = _targets(controller);
  if (targets.isEmpty) {
    _snack(context, 'No controllable outlets available.', error: true);
    return;
  }
  String target = targets.first.$1;
  var on = false;
  var minutes = 30;

  await showModalBottomSheet(
    context: context,
    useSafeArea: true,
    backgroundColor: const Color(0xFF0F1726),
    builder: (sheetContext) => StatefulBuilder(
      builder: (sheetContext, setLocal) => Padding(
        padding: const EdgeInsets.all(18),
        child: ListView(
          shrinkWrap: true,
          children: [
            const _SectionTitle(
              eyebrow: 'QUICK TIMER',
              title: 'Countdown',
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<String>(
              initialValue: target,
              decoration: const InputDecoration(labelText: 'Target outlet'),
              items: targets
                  .map(
                    (t) => DropdownMenuItem(
                      value: t.$1,
                      child: Text(t.$2),
                    ),
                  )
                  .toList(),
              onChanged: (value) => setLocal(() => target = value ?? target),
            ),
            const SizedBox(height: 10),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: on,
              title: Text(on ? 'Turn outlet on' : 'Turn outlet off'),
              onChanged: (value) => setLocal(() => on = value),
            ),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: [15, 30, 60, 120]
                  .map(
                    (value) => ChoiceChip(
                      label: Text(value < 60 ? '${value}m' : '${value ~/ 60}h'),
                      selected: minutes == value,
                      onSelected: (_) => setLocal(() => minutes = value),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () async {
                final parsed = _parseTarget(target);
                try {
                  await controller.createCountdown({
                    'mac': parsed.$1,
                    'outlet': parsed.$2,
                    'on': on,
                    'delay_seconds': minutes * 60,
                    'offline_policy': 'queue',
                  });
                  if (sheetContext.mounted) Navigator.pop(sheetContext);
                } catch (e) {
                  if (sheetContext.mounted) {
                    _snack(sheetContext, e.toString(), error: true);
                  }
                }
              },
              icon: const Icon(Icons.timer_outlined),
              label: Text('Start $minutes minute timer'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class AddStripPage extends StatefulWidget {
  final AppController controller;
  const AddStripPage({super.key, required this.controller});

  @override
  State<AddStripPage> createState() => _AddStripPageState();
}

class _AddStripPageState extends State<AddStripPage> {
  final names = <String, TextEditingController>{};
  final ssid = TextEditingController();
  final password = TextEditingController();
  final serverIp = TextEditingController();
  final deviceIp = TextEditingController(text: '192.168.1.1');

  @override
  void dispose() {
    for (final c in names.values) {
      c.dispose();
    }
    ssid.dispose();
    password.dispose();
    serverIp.dispose();
    deviceIp.dispose();
    super.dispose();
  }

  TextEditingController nameFor(Map<String, dynamic> strip) {
    final mac = strip['mac']?.toString() ?? '';
    return names.putIfAbsent(
      mac,
      () => TextEditingController(
        text: strip['name']?.toString() ?? 'Voltra ${mac.substring(math.max(0, mac.length - 4))}',
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pending = widget.controller.pendingStrips;
    return Scaffold(
      appBar: AppBar(title: const Text('Add strip')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),
        children: [
          _SectionTitle(
            eyebrow: 'DISCOVERED',
            title: 'New strips',
            trailing: IconButton(
              onPressed: widget.controller.refresh,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ),
          const SizedBox(height: 10),
          if (pending.isEmpty)
            const _EmptyCard(
              icon: Icons.wifi_find_rounded,
              title: 'Waiting for a new strip',
              text:
                  'A strip that connects to Voltra TCP 10086 will appear here automatically.',
            ),
          ...pending.map(
            (strip) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          const _LogoMark(size: 42),
                          const SizedBox(width: 11),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'New MTTL-W01',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  '${strip['mac']} · ${strip['last_ip'] ?? 'No IP'}',
                                  style: const TextStyle(
                                    color: Color(0xFF7E899D),
                                    fontSize: 9,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          _StatusPill(
                            text: strip['online'] == true ? 'READY' : 'OFFLINE',
                            active: strip['online'] == true,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: nameFor(strip),
                        decoration:
                            const InputDecoration(labelText: 'Strip name'),
                      ),
                      const SizedBox(height: 9),
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton(
                              onPressed: strip['online'] == true
                                  ? () async {
                                      try {
                                        await widget.controller.adopt(
                                          strip['mac']?.toString() ?? '',
                                          nameFor(strip).text.trim(),
                                        );
                                        if (context.mounted) {
                                          _snack(context, 'Strip added.');
                                        }
                                      } catch (e) {
                                        if (context.mounted) {
                                          _snack(
                                            context,
                                            e.toString(),
                                            error: true,
                                          );
                                        }
                                      }
                                    }
                                  : null,
                              child: const Text('Add strip'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () async {
                                await widget.controller
                                    .ignore(strip['mac']?.toString() ?? '');
                              },
                              child: const Text('Ignore'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 18),
          const _SectionTitle(
            eyebrow: 'WI-FI SETUP',
            title: 'Provision a new strip',
          ),
          const SizedBox(height: 5),
          const Text(
            'Use this while the Voltra host can reach the strip temporary TONLY_TAP network.',
            style: TextStyle(
              color: Color(0xFF818BA0),
              fontSize: 11,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  TextField(
                    controller: ssid,
                    decoration: const InputDecoration(
                      labelText: '2.4 GHz Wi-Fi SSID',
                    ),
                  ),
                  const SizedBox(height: 9),
                  TextField(
                    controller: password,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Wi-Fi password',
                    ),
                  ),
                  const SizedBox(height: 9),
                  TextField(
                    controller: serverIp,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Voltra server LAN IP',
                      hintText: '192.168.1.65',
                    ),
                  ),
                  const SizedBox(height: 9),
                  TextField(
                    controller: deviceIp,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Strip setup IP',
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: () async {
                      try {
                        await widget.controller.provision(
                          ssid: ssid.text.trim(),
                          password: password.text,
                          serverIp: serverIp.text.trim(),
                          deviceIp: deviceIp.text.trim(),
                        );
                        password.clear();
                        if (context.mounted) {
                          _snack(
                            context,
                            'Network settings sent. Wait for the strip to reconnect.',
                          );
                        }
                      } catch (e) {
                        if (context.mounted) {
                          _snack(context, e.toString(), error: true);
                        }
                      }
                    },
                    icon: const Icon(Icons.router_rounded),
                    label: const Text('Send network settings'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(50),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}


class LockScreen extends StatefulWidget {
  final SecurityController security;
  const LockScreen({super.key, required this.security});

  @override
  State<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends State<LockScreen> {
  final pin = TextEditingController();
  bool busy = false;
  String? error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && widget.security.biometricEnabled) {
        _useBiometric();
      }
    });
  }

  @override
  void dispose() {
    pin.dispose();
    super.dispose();
  }

  Future<void> _unlockWithPin() async {
    if (busy) return;
    final value = pin.text.trim();
    if (!RegExp(r'^\d{4,6}
  final AppController controller;
  final SecurityController security;
  const SettingsPage({
    super.key,
    required this.controller,
    required this.security,
  });

  @override
  Widget build(BuildContext context) {
    final online = controller.summary['online_strips'] ?? 0;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      children: [
        const _SectionTitle(
          eyebrow: 'LOCAL SERVER',
          title: 'Voltra',
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(15),
            child: Column(
              children: [
                const _LogoMark(size: 58),
                const SizedBox(height: 12),
                const Text(
                  'Voltra Mobile',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'App v${controller.appVersion} (${controller.appBuild}) · Server v${controller.version}',
                  style: const TextStyle(
                    color: Color(0xFF828C9F),
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 15),
                _SettingsLine(
                  icon: Icons.dns_rounded,
                  label: 'Server',
                  value: controller.baseUrl,
                ),
                _SettingsLine(
                  icon: Icons.wifi_rounded,
                  label: 'Online strips',
                  value: '$online',
                ),
                _SettingsLine(
                  icon: Icons.shield_outlined,
                  label: 'Connection',
                  value: 'Local LAN',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.refresh_rounded),
                title: const Text('Refresh all data'),
                onTap: controller.refresh,
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.language_rounded),
                title: const Text('Open web dashboard'),
                subtitle: Text('${controller.baseUrl}/voltra/'),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.link_off_rounded,
                  color: Color(0xFFFF7C88),
                ),
                title: const Text(
                  'Change Voltra server',
                  style: TextStyle(color: Color(0xFFFFA4AC)),
                ),
                onTap: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (dialogContext) => AlertDialog(
                      title: const Text('Disconnect server?'),
                      content: const Text(
                        'You can discover or enter another Voltra server after disconnecting.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, false),
                          child: const Text('Cancel'),
                        ),
                        FilledButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, true),
                          child: const Text('Disconnect'),
                        ),
                      ],
                    ),
                  );
                  if (ok == true) await controller.disconnect();
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _InfoRow(
          icon: Icons.lock_outline_rounded,
          title: 'No cloud account',
          text:
              'This APK talks directly to your Voltra server and does not require an external login.',
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String eyebrow;
  final String title;
  final Widget? trailing;
  const _SectionTitle({
    required this.eyebrow,
    required this.title,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                eyebrow,
                style: const TextStyle(
                  color: Color(0xFF39E27D),
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -.5,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class _EmptyCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _EmptyCard({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1624),
        borderRadius: BorderRadius.circular(19),
        border: Border.all(color: const Color(0xFF273249)),
      ),
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: const Color(0xFF123128),
              borderRadius: BorderRadius.circular(15),
            ),
            child: Icon(icon, color: const Color(0xFF39E27D)),
          ),
          const SizedBox(height: 11),
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF7B869B),
              fontSize: 10,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final bool accent;
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    this.accent = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color:
            accent ? const Color(0xFF11281F) : const Color(0xFF101827),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color:
              accent ? const Color(0xFF276B4A) : const Color(0xFF222D42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const Spacer(),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF7F899E),
              fontSize: 9,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: const Color(0xFF123128),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: const Color(0xFF39E27D)),
              ),
              const SizedBox(height: 13),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(
                  color: Color(0xFF7B859A),
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String text;
  final bool active;
  const _StatusPill({required this.text, required this.active});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color:
            active ? const Color(0xFF112C24) : const Color(0xFF171F2C),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color:
              active ? const Color(0xFF286248) : const Color(0xFF343E51),
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          color:
              active ? const Color(0xFF69E5A0) : const Color(0xFF909AAD),
          fontSize: 8,
          fontWeight: FontWeight.w900,
          letterSpacing: .8,
        ),
      ),
    );
  }
}

class _PulseDot extends StatelessWidget {
  final bool active;
  const _PulseDot({this.active = true});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: active
            ? const Color(0xFF39E27D)
            : const Color(0xFF6D778D),
        shape: BoxShape.circle,
        boxShadow: active
            ? const [
                BoxShadow(
                  color: Color(0x8839E27D),
                  blurRadius: 9,
                ),
              ]
            : null,
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  final String value;
  final String label;
  const _MiniMetric({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: value,
            style: const TextStyle(
              color: Color(0xFFC6CBD6),
              fontWeight: FontWeight.w800,
            ),
          ),
          TextSpan(text: ' $label'),
        ],
      ),
      style: const TextStyle(
        color: Color(0xFF8D96AA),
        fontSize: 10,
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  final int value;
  const _CountBadge({required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 31),
      height: 31,
      padding: const EdgeInsets.symmetric(horizontal: 9),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFF253047)),
      ),
      child: Text(
        '$value',
        style: const TextStyle(
          color: Color(0xFFABB3C2),
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _InfoRow({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  text,
                  style: const TextStyle(
                    color: Color(0xFF7C879B),
                    fontSize: 10,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsLine extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _SettingsLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Icon(icon, size: 18, color: const Color(0xFF7F8A9E)),
          const SizedBox(width: 10),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF8A94A7),
              fontSize: 11,
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 10,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

List<(String, String)> _targets(AppController controller) {
  final result = <(String, String)>[];
  for (final strip in controller.activeStrips) {
    if (strip['online'] != true ||
        strip['enabled'] == false ||
        strip['state'] != 'active') {
      continue;
    }
    final mac = strip['mac']?.toString() ?? '';
    final name = strip['name']?.toString() ?? mac;
    for (var outlet = 1; outlet <= 4; outlet++) {
      result.add(('$mac:$outlet', '$name · Outlet $outlet'));
    }
  }
  return result;
}

(String, int) _parseTarget(String value) {
  final index = value.lastIndexOf(':');
  if (index < 1) throw const VoltraException('Invalid outlet target.');
  return (
    value.substring(0, index),
    int.parse(value.substring(index + 1)),
  );
}

double _num(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

void _snack(
  BuildContext context,
  String message, {
  bool error = false,
}) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(message),
      backgroundColor:
          error ? const Color(0xFF4A1F29) : const Color(0xFF153425),
    ),
  );
}
).hasMatch(value)) {
      setState(() => error = 'Enter your 4 to 6 digit PIN.');
      return;
    }

    setState(() {
      busy = true;
      error = null;
    });
    final ok = await widget.security.verifyPin(value);
    if (!mounted) return;
    setState(() {
      busy = false;
      if (!ok) error = 'Incorrect PIN. Try again.';
    });
    if (!ok) {
      pin
        ..clear()
        ..selection = const TextSelection.collapsed(offset: 0);
    }
  }

  Future<void> _useBiometric() async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    final ok = await widget.security.authenticateBiometric();
    if (!mounted) return;
    setState(() {
      busy = false;
      if (!ok) error = 'Biometric unlock was not completed.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 430),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const _LogoMark(size: 72),
                  const SizedBox(height: 24),
                  const Text(
                    'Voltra is locked',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Unlock before controlling outlets, schedules, or server settings.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFF8993A7),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: pin,
                    enabled: !busy,
                    autofocus: !widget.security.biometricEnabled,
                    obscureText: true,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 8,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'PIN',
                      hintText: '••••',
                      counterText: '',
                    ),
                    onSubmitted: (_) => _unlockWithPin(),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFFFF8A95)),
                    ),
                  ],
                  const SizedBox(height: 14),
                  FilledButton.icon(
                    onPressed: busy ? null : _unlockWithPin,
                    icon: busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.lock_open_rounded),
                    label: const Text('Unlock Voltra'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                  ),
                  if (widget.security.biometricEnabled) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: busy ? null : _useBiometric,
                      icon: const Icon(Icons.fingerprint_rounded),
                      label: const Text('Use biometrics'),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(50),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  const _InfoRow(
                    icon: Icons.shield_outlined,
                    title: 'Local protection',
                    text:
                        'Your PIN stays on this device and is stored as a salted hash.',
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

Future<String?> _showSetPinDialog(BuildContext context) async {
  final first = TextEditingController();
  final confirm = TextEditingController();
  String? error;

  final result = await showDialog<String>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setLocal) => AlertDialog(
        title: const Text('Create Voltra PIN'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Choose a 4 to 6 digit PIN. You can also enable biometrics after the PIN is created.',
              style: TextStyle(fontSize: 12, height: 1.45),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: first,
              autofocus: true,
              obscureText: true,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(
                labelText: 'New PIN',
                counterText: '',
              ),
            ),
            const SizedBox(height: 9),
            TextField(
              controller: confirm,
              obscureText: true,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(
                labelText: 'Confirm PIN',
                counterText: '',
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 8),
              Text(
                error!,
                style: const TextStyle(
                  color: Color(0xFFFF8A95),
                  fontSize: 11,
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final value = first.text.trim();
              if (!RegExp(r'^\d{4,6}
  final AppController controller;
  final SecurityController security;
  const SettingsPage({
    super.key,
    required this.controller,
    required this.security,
  });

  @override
  Widget build(BuildContext context) {
    final online = controller.summary['online_strips'] ?? 0;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      children: [
        const _SectionTitle(
          eyebrow: 'LOCAL SERVER',
          title: 'Voltra',
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(15),
            child: Column(
              children: [
                const _LogoMark(size: 58),
                const SizedBox(height: 12),
                const Text(
                  'Voltra Mobile',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'App v${controller.appVersion} (${controller.appBuild}) · Server v${controller.version}',
                  style: const TextStyle(
                    color: Color(0xFF828C9F),
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 15),
                _SettingsLine(
                  icon: Icons.dns_rounded,
                  label: 'Server',
                  value: controller.baseUrl,
                ),
                _SettingsLine(
                  icon: Icons.wifi_rounded,
                  label: 'Online strips',
                  value: '$online',
                ),
                _SettingsLine(
                  icon: Icons.shield_outlined,
                  label: 'Connection',
                  value: 'Local LAN',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.refresh_rounded),
                title: const Text('Refresh all data'),
                onTap: controller.refresh,
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.language_rounded),
                title: const Text('Open web dashboard'),
                subtitle: Text('${controller.baseUrl}/voltra/'),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.link_off_rounded,
                  color: Color(0xFFFF7C88),
                ),
                title: const Text(
                  'Change Voltra server',
                  style: TextStyle(color: Color(0xFFFFA4AC)),
                ),
                onTap: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (dialogContext) => AlertDialog(
                      title: const Text('Disconnect server?'),
                      content: const Text(
                        'You can discover or enter another Voltra server after disconnecting.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, false),
                          child: const Text('Cancel'),
                        ),
                        FilledButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, true),
                          child: const Text('Disconnect'),
                        ),
                      ],
                    ),
                  );
                  if (ok == true) await controller.disconnect();
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _InfoRow(
          icon: Icons.lock_outline_rounded,
          title: 'No cloud account',
          text:
              'This APK talks directly to your Voltra server and does not require an external login.',
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String eyebrow;
  final String title;
  final Widget? trailing;
  const _SectionTitle({
    required this.eyebrow,
    required this.title,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                eyebrow,
                style: const TextStyle(
                  color: Color(0xFF39E27D),
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -.5,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class _EmptyCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _EmptyCard({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1624),
        borderRadius: BorderRadius.circular(19),
        border: Border.all(color: const Color(0xFF273249)),
      ),
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: const Color(0xFF123128),
              borderRadius: BorderRadius.circular(15),
            ),
            child: Icon(icon, color: const Color(0xFF39E27D)),
          ),
          const SizedBox(height: 11),
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF7B869B),
              fontSize: 10,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final bool accent;
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    this.accent = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color:
            accent ? const Color(0xFF11281F) : const Color(0xFF101827),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color:
              accent ? const Color(0xFF276B4A) : const Color(0xFF222D42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const Spacer(),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF7F899E),
              fontSize: 9,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: const Color(0xFF123128),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: const Color(0xFF39E27D)),
              ),
              const SizedBox(height: 13),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(
                  color: Color(0xFF7B859A),
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String text;
  final bool active;
  const _StatusPill({required this.text, required this.active});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color:
            active ? const Color(0xFF112C24) : const Color(0xFF171F2C),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color:
              active ? const Color(0xFF286248) : const Color(0xFF343E51),
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          color:
              active ? const Color(0xFF69E5A0) : const Color(0xFF909AAD),
          fontSize: 8,
          fontWeight: FontWeight.w900,
          letterSpacing: .8,
        ),
      ),
    );
  }
}

class _PulseDot extends StatelessWidget {
  final bool active;
  const _PulseDot({this.active = true});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: active
            ? const Color(0xFF39E27D)
            : const Color(0xFF6D778D),
        shape: BoxShape.circle,
        boxShadow: active
            ? const [
                BoxShadow(
                  color: Color(0x8839E27D),
                  blurRadius: 9,
                ),
              ]
            : null,
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  final String value;
  final String label;
  const _MiniMetric({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: value,
            style: const TextStyle(
              color: Color(0xFFC6CBD6),
              fontWeight: FontWeight.w800,
            ),
          ),
          TextSpan(text: ' $label'),
        ],
      ),
      style: const TextStyle(
        color: Color(0xFF8D96AA),
        fontSize: 10,
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  final int value;
  const _CountBadge({required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 31),
      height: 31,
      padding: const EdgeInsets.symmetric(horizontal: 9),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFF253047)),
      ),
      child: Text(
        '$value',
        style: const TextStyle(
          color: Color(0xFFABB3C2),
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _InfoRow({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  text,
                  style: const TextStyle(
                    color: Color(0xFF7C879B),
                    fontSize: 10,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsLine extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _SettingsLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Icon(icon, size: 18, color: const Color(0xFF7F8A9E)),
          const SizedBox(width: 10),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF8A94A7),
              fontSize: 11,
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 10,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

List<(String, String)> _targets(AppController controller) {
  final result = <(String, String)>[];
  for (final strip in controller.activeStrips) {
    if (strip['online'] != true ||
        strip['enabled'] == false ||
        strip['state'] != 'active') {
      continue;
    }
    final mac = strip['mac']?.toString() ?? '';
    final name = strip['name']?.toString() ?? mac;
    for (var outlet = 1; outlet <= 4; outlet++) {
      result.add(('$mac:$outlet', '$name · Outlet $outlet'));
    }
  }
  return result;
}

(String, int) _parseTarget(String value) {
  final index = value.lastIndexOf(':');
  if (index < 1) throw const VoltraException('Invalid outlet target.');
  return (
    value.substring(0, index),
    int.parse(value.substring(index + 1)),
  );
}

double _num(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

void _snack(
  BuildContext context,
  String message, {
  bool error = false,
}) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(message),
      backgroundColor:
          error ? const Color(0xFF4A1F29) : const Color(0xFF153425),
    ),
  );
}
).hasMatch(value)) {
                setLocal(() => error = 'PIN must contain 4 to 6 digits.');
                return;
              }
              if (value != confirm.text.trim()) {
                setLocal(() => error = 'PIN confirmation does not match.');
                return;
              }
              Navigator.pop(dialogContext, value);
            },
            child: const Text('Enable lock'),
          ),
        ],
      ),
    ),
  );

  first.dispose();
  confirm.dispose();
  return result;
}

Future<bool> _verifySecurityPin(
  BuildContext context,
  SecurityController security,
) async {
  final pin = TextEditingController();
  String? error;
  bool busy = false;

  final result = await showDialog<bool>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setLocal) => AlertDialog(
        title: const Text('Confirm Voltra PIN'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Enter your current PIN to turn off app lock.',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: pin,
              autofocus: true,
              enabled: !busy,
              obscureText: true,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(
                labelText: 'Current PIN',
                counterText: '',
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 8),
              Text(
                error!,
                style: const TextStyle(
                  color: Color(0xFFFF8A95),
                  fontSize: 11,
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: busy ? null : () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: busy
                ? null
                : () async {
                    setLocal(() {
                      busy = true;
                      error = null;
                    });
                    final ok = await security.verifyPin(
                      pin.text.trim(),
                      unlockOnSuccess: false,
                    );
                    if (!dialogContext.mounted) return;
                    if (ok) {
                      Navigator.pop(dialogContext, true);
                    } else {
                      setLocal(() {
                        busy = false;
                        error = 'Incorrect PIN.';
                      });
                      pin.clear();
                    }
                  },
            child: Text(busy ? 'Checking…' : 'Confirm'),
          ),
        ],
      ),
    ),
  );

  pin.dispose();
  return result == true;
}

Future<int?> _chooseAutoLock(
  BuildContext context,
  int current,
) {
  const options = <int>[0, 30, 60, 300];
  return showDialog<int>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Auto-lock'),
      children: [
        for (final seconds in options)
          RadioListTile<int>(
            value: seconds,
            groupValue: current,
            title: Text(_autoLockLabel(seconds)),
            onChanged: (value) => Navigator.pop(dialogContext, value),
          ),
      ],
    ),
  );
}

String _autoLockLabel(int seconds) {
  if (seconds == 0) return 'Immediately';
  if (seconds < 60) return '$seconds seconds';
  if (seconds == 60) return '1 minute';
  return '${seconds ~/ 60} minutes';
}

class SettingsPage extends StatelessWidget {
  final AppController controller;
  final SecurityController security;
  const SettingsPage({
    super.key,
    required this.controller,
    required this.security,
  });

  @override
  Widget build(BuildContext context) {
    final online = controller.summary['online_strips'] ?? 0;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      children: [
        const _SectionTitle(
          eyebrow: 'LOCAL SERVER',
          title: 'Voltra',
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(15),
            child: Column(
              children: [
                const _LogoMark(size: 58),
                const SizedBox(height: 12),
                const Text(
                  'Voltra Mobile',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'App v${controller.appVersion} (${controller.appBuild}) · Server v${controller.version}',
                  style: const TextStyle(
                    color: Color(0xFF828C9F),
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 15),
                _SettingsLine(
                  icon: Icons.dns_rounded,
                  label: 'Server',
                  value: controller.baseUrl,
                ),
                _SettingsLine(
                  icon: Icons.wifi_rounded,
                  label: 'Online strips',
                  value: '$online',
                ),
                _SettingsLine(
                  icon: Icons.shield_outlined,
                  label: 'Connection',
                  value: 'Local LAN',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.refresh_rounded),
                title: const Text('Refresh all data'),
                onTap: controller.refresh,
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.language_rounded),
                title: const Text('Open web dashboard'),
                subtitle: Text('${controller.baseUrl}/voltra/'),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.link_off_rounded,
                  color: Color(0xFFFF7C88),
                ),
                title: const Text(
                  'Change Voltra server',
                  style: TextStyle(color: Color(0xFFFFA4AC)),
                ),
                onTap: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (dialogContext) => AlertDialog(
                      title: const Text('Disconnect server?'),
                      content: const Text(
                        'You can discover or enter another Voltra server after disconnecting.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, false),
                          child: const Text('Cancel'),
                        ),
                        FilledButton(
                          onPressed: () =>
                              Navigator.pop(dialogContext, true),
                          child: const Text('Disconnect'),
                        ),
                      ],
                    ),
                  );
                  if (ok == true) await controller.disconnect();
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _SectionTitle(
          eyebrow: 'SECURITY',
          title: 'App lock',
        ),
        const SizedBox(height: 10),
        Card(
          child: Column(
            children: [
              SwitchListTile(
                secondary: const Icon(Icons.lock_outline_rounded),
                value: security.enabled,
                title: const Text('Protect Voltra'),
                subtitle: Text(
                  security.enabled
                      ? 'PIN is required after Voltra auto-locks.'
                      : 'Add a local PIN before anyone can control your strips.',
                ),
                onChanged: (value) async {
                  if (value) {
                    final pin = await _showSetPinDialog(context);
                    if (pin == null) return;
                    try {
                      await security.enableWithPin(pin);
                      if (context.mounted) {
                        _snack(context, 'Voltra app lock enabled.');
                      }
                    } catch (e) {
                      if (context.mounted) {
                        _snack(context, e.toString(), error: true);
                      }
                    }
                    return;
                  }

                  final confirmed =
                      await _verifySecurityPin(context, security);
                  if (!confirmed) return;
                  await security.disable();
                  if (context.mounted) {
                    _snack(context, 'Voltra app lock disabled.');
                  }
                },
              ),
              if (security.enabled) ...[
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.fingerprint_rounded),
                  value: security.biometricEnabled,
                  title: const Text('Biometric unlock'),
                  subtitle: Text(
                    security.canUseBiometrics
                        ? 'Use fingerprint or face authentication on this device.'
                        : 'No supported biometric authentication is available.',
                  ),
                  onChanged: security.canUseBiometrics
                      ? (value) async {
                          final ok =
                              await security.setBiometricEnabled(value);
                          if (context.mounted && value && !ok) {
                            _snack(
                              context,
                              'Biometric authentication was not completed.',
                              error: true,
                            );
                          }
                        }
                      : null,
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.timer_outlined),
                  title: const Text('Auto-lock'),
                  subtitle: const Text(
                    'Lock Voltra after the app stays in the background.',
                  ),
                  trailing: Text(_autoLockLabel(security.autoLockSeconds)),
                  onTap: () async {
                    final seconds = await _chooseAutoLock(
                      context,
                      security.autoLockSeconds,
                    );
                    if (seconds != null) {
                      await security.setAutoLockSeconds(seconds);
                    }
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.lock_clock_outlined),
                  title: const Text('Lock now'),
                  subtitle: const Text('Require PIN or biometrics immediately.'),
                  onTap: security.lock,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _InfoRow(
          icon: Icons.lock_outline_rounded,
          title: 'No cloud account',
          text:
              'This APK talks directly to your Voltra server and does not require an external login.',
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String eyebrow;
  final String title;
  final Widget? trailing;
  const _SectionTitle({
    required this.eyebrow,
    required this.title,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                eyebrow,
                style: const TextStyle(
                  color: Color(0xFF39E27D),
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -.5,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class _EmptyCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _EmptyCard({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1624),
        borderRadius: BorderRadius.circular(19),
        border: Border.all(color: const Color(0xFF273249)),
      ),
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: const Color(0xFF123128),
              borderRadius: BorderRadius.circular(15),
            ),
            child: Icon(icon, color: const Color(0xFF39E27D)),
          ),
          const SizedBox(height: 11),
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF7B869B),
              fontSize: 10,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final bool accent;
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    this.accent = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color:
            accent ? const Color(0xFF11281F) : const Color(0xFF101827),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color:
              accent ? const Color(0xFF276B4A) : const Color(0xFF222D42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const Spacer(),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF7F899E),
              fontSize: 9,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: const Color(0xFF123128),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: const Color(0xFF39E27D)),
              ),
              const SizedBox(height: 13),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(
                  color: Color(0xFF7B859A),
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String text;
  final bool active;
  const _StatusPill({required this.text, required this.active});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color:
            active ? const Color(0xFF112C24) : const Color(0xFF171F2C),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color:
              active ? const Color(0xFF286248) : const Color(0xFF343E51),
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          color:
              active ? const Color(0xFF69E5A0) : const Color(0xFF909AAD),
          fontSize: 8,
          fontWeight: FontWeight.w900,
          letterSpacing: .8,
        ),
      ),
    );
  }
}

class _PulseDot extends StatelessWidget {
  final bool active;
  const _PulseDot({this.active = true});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: active
            ? const Color(0xFF39E27D)
            : const Color(0xFF6D778D),
        shape: BoxShape.circle,
        boxShadow: active
            ? const [
                BoxShadow(
                  color: Color(0x8839E27D),
                  blurRadius: 9,
                ),
              ]
            : null,
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  final String value;
  final String label;
  const _MiniMetric({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: value,
            style: const TextStyle(
              color: Color(0xFFC6CBD6),
              fontWeight: FontWeight.w800,
            ),
          ),
          TextSpan(text: ' $label'),
        ],
      ),
      style: const TextStyle(
        color: Color(0xFF8D96AA),
        fontSize: 10,
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  final int value;
  const _CountBadge({required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 31),
      height: 31,
      padding: const EdgeInsets.symmetric(horizontal: 9),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0xFF101827),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFF253047)),
      ),
      child: Text(
        '$value',
        style: const TextStyle(
          color: Color(0xFFABB3C2),
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String text;
  const _InfoRow({
    required this.icon,
    required this.title,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF39E27D), size: 19),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  text,
                  style: const TextStyle(
                    color: Color(0xFF7C879B),
                    fontSize: 10,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsLine extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _SettingsLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Icon(icon, size: 18, color: const Color(0xFF7F8A9E)),
          const SizedBox(width: 10),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF8A94A7),
              fontSize: 11,
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 10,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

List<(String, String)> _targets(AppController controller) {
  final result = <(String, String)>[];
  for (final strip in controller.activeStrips) {
    if (strip['online'] != true ||
        strip['enabled'] == false ||
        strip['state'] != 'active') {
      continue;
    }
    final mac = strip['mac']?.toString() ?? '';
    final name = strip['name']?.toString() ?? mac;
    for (var outlet = 1; outlet <= 4; outlet++) {
      result.add(('$mac:$outlet', '$name · Outlet $outlet'));
    }
  }
  return result;
}

(String, int) _parseTarget(String value) {
  final index = value.lastIndexOf(':');
  if (index < 1) throw const VoltraException('Invalid outlet target.');
  return (
    value.substring(0, index),
    int.parse(value.substring(index + 1)),
  );
}

double _num(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

void _snack(
  BuildContext context,
  String message, {
  bool error = false,
}) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(message),
      backgroundColor:
          error ? const Color(0xFF4A1F29) : const Color(0xFF153425),
    ),
  );
}
