import 'package:flutter/material.dart';

import 'app_controller.dart';

/// Real server-backed management of one outlet. Nothing here is demo-only.
class OutletSettingsSheet extends StatefulWidget {
  const OutletSettingsSheet({
    super.key,
    required this.controller,
    required this.strip,
    required this.channel,
  });

  final AppController controller;
  final Map<String, dynamic> strip;
  final int channel;

  @override
  State<OutletSettingsSheet> createState() => _OutletSettingsSheetState();
}

class _OutletSettingsSheetState extends State<OutletSettingsSheet> {
  static const green = Color(0xFF39E27D);
  final name = TextEditingController();
  final autoMinutes = TextEditingController(text: '0');
  final lowThreshold = TextEditingController(text: '5');
  final lowDuration = TextEditingController(text: '300');
  final alertThreshold = TextEditingController(text: '0');
  final sceneName = TextEditingController();
  String icon = 'plug';
  String restore = 'none';
  bool protection = false;
  bool locked = false;
  bool notifications = true;
  bool lowPower = false;
  bool pending = false;
  bool timerOn = false;
  bool scheduledOn = false;
  bool sceneOn = true;
  int timerMinutes = 30;
  TimeOfDay scheduleTime = const TimeOfDay(hour: 23, minute: 0);
  Set<int> days = {0, 1, 2, 3, 4, 5, 6};
  Map<String, dynamic>? dailyEnergy;
  Map<String, dynamic>? monthlyEnergy;
  List<Map<String, dynamic>> activity = [];

  String get mac => widget.strip['mac']?.toString() ?? '';
  String get outletLabel => name.text.trim().isEmpty ? 'مخرج ${widget.channel}' : name.text.trim();
  TextDirection get nameDirection =>
      RegExp(r'[\u0600-\u06FF]').hasMatch(name.text) ? TextDirection.rtl : TextDirection.ltr;

  @override
  void initState() {
    super.initState();
    final raw = widget.strip['outlets'];
    if (raw is List) {
      for (final item in raw) {
        if (item is Map && item['channel'] == widget.channel && item['preferences'] is Map) {
          _apply(Map<String, dynamic>.from(item['preferences']));
          break;
        }
      }
    }
    name.addListener(_updateNameDirection);
    _load();
  }

  void _updateNameDirection() {
    if (mounted) setState(() {});
  }

  void _apply(Map<String, dynamic> prefs) {
    name.text = prefs['name']?.toString() ?? '';
    icon = prefs['icon']?.toString() ?? 'plug';
    restore = prefs['restore_policy']?.toString() ?? 'none';
    protection = prefs['protected'] == true;
    locked = prefs['locked'] == true;
    notifications = prefs['notify'] != false;
    lowPower = prefs['low_power_enabled'] == true;
    autoMinutes.text = '${prefs['auto_off_minutes'] ?? 0}';
    lowThreshold.text = '${prefs['low_power_threshold_w'] ?? 5}';
    lowDuration.text = '${prefs['low_power_duration_s'] ?? 300}';
    alertThreshold.text = '${prefs['alert_above_w'] ?? 0}';
  }

  Future<void> _load() async {
    try {
      final result = await Future.wait<dynamic>([
        widget.controller.getOutletPrefs(mac, widget.channel),
        widget.controller.energy(mac, 24, outlet: widget.channel),
        widget.controller.energy(mac, 720, outlet: widget.channel),
        widget.controller.outletActivity(mac, widget.channel),
      ]);
      if (!mounted) return;
      setState(() {
        _apply(Map<String, dynamic>.from(result[0] as Map));
        dailyEnergy = Map<String, dynamic>.from((result[1] as Map)['summary'] as Map);
        monthlyEnergy = Map<String, dynamic>.from((result[2] as Map)['summary'] as Map);
        activity = (result[3] as List).cast<Map<String, dynamic>>();
      });
    } catch (error) {
      if (mounted) _show('Could not load all outlet details: $error', error: true);
    }
  }

  void _show(String value, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(value, textDirection: RegExp(r'[\u0600-\u06FF]').hasMatch(value)
          ? TextDirection.rtl : TextDirection.ltr),
      backgroundColor: error ? const Color(0xFF71303C) : const Color(0xFF134F39),
    ));
  }

  Future<void> _perform(Future<void> Function() command, String message) async {
    if (pending) return;
    setState(() => pending = true);
    try {
      await command();
      if (mounted) _show(message);
    } catch (error) {
      if (mounted) _show(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => pending = false);
    }
  }

  Future<void> _save() => _perform(() async {
    await widget.controller.saveOutletPrefs(mac, widget.channel, {
      'name': name.text.trim(),
      'icon': icon, 'protected': protection, 'locked': locked,
      'notify': notifications, 'restore_policy': restore,
      'auto_off_minutes': int.tryParse(autoMinutes.text) ?? 0,
      'low_power_enabled': lowPower,
      'low_power_threshold_w': double.tryParse(lowThreshold.text) ?? 5,
      'low_power_duration_s': int.tryParse(lowDuration.text) ?? 300,
      'alert_above_w': double.tryParse(alertThreshold.text) ?? 0,
    });
  }, 'تم حفظ إعدادات المخرج');

  @override
  void dispose() {
    name.removeListener(_updateNameDirection);
    for (final item in [name, autoMinutes, lowThreshold, lowDuration, alertThreshold, sceneName]) {
      item.dispose();
    }
    super.dispose();
  }

  Widget _heading(String title) => Padding(
    padding: const EdgeInsets.only(top: 14, bottom: 8),
    child: Text(title, style: const TextStyle(color: green, fontSize: 15, fontWeight: FontWeight.w800)),
  );

  Widget _numeric(TextEditingController controller, String label) => TextField(
    controller: controller, keyboardType: const TextInputType.numberWithOptions(decimal: true),
    decoration: InputDecoration(labelText: label),
  );

  List<Map<String, dynamic>> get schedules {
    final values = widget.controller.automation['schedules'];
    if (values is! Map) return [];
    return values.values.whereType<Map>()
        .map((x) => Map<String, dynamic>.from(x))
        .where((x) => x['mac'] == mac && x['outlet'] == widget.channel && x['enabled'] != false)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final price = ((widget.controller.overview?['settings'] as Map?)?['energy_price_per_kwh'] as num?)?.toDouble() ?? 0.0;
    final currency = ((widget.controller.overview?['settings'] as Map?)?['currency'] ?? 'EGP').toString();
    final dayKwh = (dailyEnergy?['energy_kwh'] as num?)?.toDouble() ?? 0;
    final monthKwh = (monthlyEnergy?['energy_kwh'] as num?)?.toDouble() ?? 0;
    final rows = widget.strip['outlets'];
    final row = rows is List
        ? rows.whereType<Map>().where((x) => x['channel'] == widget.channel).toList()
        : <Map>[];
    final watts = row.isEmpty ? 0.0 : (row.first['power_w'] as num?)?.toDouble() ?? 0;
    final fields = [
      SwitchListTile(
        title: const Text('🛡 حماية من الفصل'),
        subtitle: const Text('يسأل قبل الإيقاف اليدوي ويمنع الإيقاف التلقائي'),
        value: protection, onChanged: pending ? null : (v) => setState(() => protection = v),
      ),
      SwitchListTile(
        title: const Text('🔒 قفل المخرج'),
        subtitle: const Text('يمنع التشغيل والإيقاف حتى إلغاء القفل'),
        value: locked, onChanged: pending ? null : (v) => setState(() => locked = v),
      ),
      SwitchListTile(
        title: const Text('🔔 إشعارات النشاط'),
        subtitle: const Text('تظهر عند فتح التطبيق ومتابعة الأنشطة'),
        value: notifications, onChanged: pending ? null : (v) => setState(() => notifications = v),
      ),
    ];
    return Directionality(
      textDirection: TextDirection.rtl,
      child: ListView(
        padding: EdgeInsets.fromLTRB(16, 12, 16, 24 + MediaQuery.viewInsetsOf(context).bottom),
        children: [
          Row(children: [
            const Icon(Icons.settings_input_component_rounded, color: green),
            const SizedBox(width: 8),
            Expanded(child: Text('إعدادات $outletLabel', maxLines: 2,
              style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold))),
            IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
          ]),
          const SizedBox(height: 10),
          Card(child: Padding(padding: const EdgeInsets.all(12),
            child: Wrap(spacing: 18, runSpacing: 8, children: [
              Text('الآن: ${watts.toStringAsFixed(1)} W'),
              Text('آخر 24 ساعة: ${dayKwh.toStringAsFixed(3)} kWh'),
              Text('التكلفة آخر 30 يوم: ${(monthKwh * price).toStringAsFixed(2)} $currency'),
            ]))),
          _heading('الاسم والأيقونة'),
          TextField(
            controller: name,
            textDirection: nameDirection,
            textAlign: nameDirection == TextDirection.rtl ? TextAlign.right : TextAlign.left,
            maxLength: 80,
            decoration: const InputDecoration(labelText: 'اسم المخرج بالعربي أو الإنجليزي'),
          ),
          DropdownButtonFormField<String>(
            key: ValueKey('icon-$icon'), initialValue: icon,
            decoration: const InputDecoration(labelText: 'الأيقونة'),
            items: const [
              DropdownMenuItem(value: 'plug', child: Text('🔌 مقبس')),
              DropdownMenuItem(value: 'gamepad', child: Text('🎮 ألعاب')),
              DropdownMenuItem(value: 'tv', child: Text('📺 تلفزيون')),
              DropdownMenuItem(value: 'pc', child: Text('💻 كمبيوتر')),
              DropdownMenuItem(value: 'router', child: Text('📡 راوتر')),
              DropdownMenuItem(value: 'lamp', child: Text('💡 مصباح')),
              DropdownMenuItem(value: 'fan', child: Text('🌀 مروحة')),
              DropdownMenuItem(value: 'other', child: Text('⚡ أخرى')),
            ],
            onChanged: pending ? null : (v) => setState(() => icon = v ?? icon),
          ),
          _heading('الحماية والتنبيهات'),
          ...fields,
          _heading('إيقاف تلقائي وتنبيهات الاستهلاك'),
          _numeric(autoMinutes, 'الفصل بعد التشغيل بالدقائق (0 = إيقاف)'),
          SwitchListTile(
            title: const Text('فصل عند انخفاض الاستهلاك'),
            value: lowPower, onChanged: pending ? null : (v) => setState(() => lowPower = v),
          ),
          if (lowPower) ...[
            _numeric(lowThreshold, 'الحد الأدنى للاستهلاك W'),
            const SizedBox(height: 8),
            _numeric(lowDuration, 'مدة الانخفاض بالثواني'),
          ],
          const SizedBox(height: 8),
          _numeric(alertThreshold, 'تنبيه عند تجاوز W (0 = إيقاف)'),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: ValueKey('restore-$restore'), initialValue: restore,
            decoration: const InputDecoration(labelText: 'عند إعادة الاتصال بالسيرفر'),
            items: const [
              DropdownMenuItem(value: 'none', child: Text('عدم تغيير الحالة (آمن)')),
              DropdownMenuItem(value: 'off', child: Text('إيقاف المخرج')),
              DropdownMenuItem(value: 'last', child: Text('استعادة آخر حالة مؤكدة')),
            ],
            onChanged: pending ? null : (v) => setState(() => restore = v ?? restore),
          ),
          const SizedBox(height: 8),
          const Text('سياسة الرجوع تعمل عند إعادة الاتصال بالسيرفر، وليس كل انقطاع كهرباء.',
            style: TextStyle(fontSize: 11, color: Colors.white60)),
          const SizedBox(height: 10),
          FilledButton.icon(onPressed: pending ? null : _save,
            icon: const Icon(Icons.save), label: Text(pending ? 'جارٍ الحفظ…' : 'حفظ الإعدادات')),
          _heading('مؤقت سريع'),
          Row(children: [
            Expanded(child: DropdownButtonFormField<int>(
              initialValue: timerMinutes,
              decoration: const InputDecoration(labelText: 'المدة'),
              items: [15, 30, 60, 120, 240].map((v) => DropdownMenuItem(
                value: v, child: Text('$v دقيقة'))).toList(),
              onChanged: pending ? null : (v) => setState(() => timerMinutes = v ?? 30),
            )),
            const SizedBox(width: 8),
            Expanded(child: SwitchListTile(
              title: Text(timerOn ? 'تشغيل' : 'إيقاف'),
              value: timerOn, onChanged: pending ? null : (v) => setState(() => timerOn = v),
            )),
          ]),
          OutlinedButton.icon(
            onPressed: pending ? null : () => _perform(() =>
              widget.controller.createCountdown({'mac': mac, 'outlet': widget.channel,
                'on': timerOn, 'delay_seconds': timerMinutes * 60, 'offline_policy': 'skip'}),
              'تم ضبط المؤقت'),
            icon: const Icon(Icons.timer), label: const Text('تفعيل المؤقت'),
          ),
          _heading('جدول أسبوعي'),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('وقت التنفيذ'),
            subtitle: Text(scheduleTime.format(context)),
            trailing: const Icon(Icons.access_time),
            onTap: () async {
              final result = await showTimePicker(context: context, initialTime: scheduleTime);
              if (result != null && mounted) setState(() => scheduleTime = result);
            },
          ),
          SwitchListTile(title: Text(scheduledOn ? 'تشغيل في الوقت المحدد' : 'إيقاف في الوقت المحدد'),
            value: scheduledOn, onChanged: pending ? null : (v) => setState(() => scheduledOn = v)),
          Wrap(spacing: 5, children: [
            for (var index = 0; index < 7; index++)
              FilterChip(label: Text(['إث', 'ثل', 'أر', 'خم', 'جم', 'سب', 'أح'][index]),
                selected: days.contains(index), onSelected: (yes) =>
                  setState(() => yes ? days.add(index) : days.remove(index))),
          ]),
          OutlinedButton.icon(
            onPressed: pending || days.isEmpty ? null : () => _perform(() =>
              widget.controller.createSchedule({
                'mac': mac, 'outlet': widget.channel, 'on': scheduledOn,
                'time': '${scheduleTime.hour.toString().padLeft(2, '0')}:${scheduleTime.minute.toString().padLeft(2, '0')}',
                'days': days.toList()..sort(), 'offline_policy': 'skip',
              }), 'تم حفظ الجدول'),
            icon: const Icon(Icons.schedule), label: const Text('إضافة جدول'),
          ),
          for (final schedule in schedules)
            ListTile(
              dense: true,
              title: Text('${schedule['on'] == true ? 'تشغيل' : 'إيقاف'} · ${schedule['time'] ?? schedule['run_at'] ?? ''}'),
              trailing: IconButton(icon: const Icon(Icons.delete_outline), onPressed: pending ? null : () =>
                _perform(() => widget.controller.deleteSchedule(schedule['id'].toString()), 'تم حذف الجدول')),
            ),
          _heading('مشهد سريع'),
          TextField(
            controller: sceneName,
            textDirection: RegExp(r'[\u0600-\u06FF]').hasMatch(sceneName.text)
                ? TextDirection.rtl : TextDirection.ltr,
            decoration: const InputDecoration(labelText: 'اسم المشهد'),
            maxLength: 100,
            onChanged: (_) => setState(() {}),
          ),
          SwitchListTile(title: Text(sceneOn ? 'المشهد يشغّل المخرج' : 'المشهد يوقف المخرج'),
            value: sceneOn, onChanged: pending ? null : (v) => setState(() => sceneOn = v)),
          OutlinedButton.icon(
            onPressed: pending || sceneName.text.trim().isEmpty ? null : () => _perform(
              () => widget.controller.createScene(sceneName.text.trim(), mac, widget.channel, sceneOn),
              'تم إنشاء المشهد'),
            icon: const Icon(Icons.auto_awesome), label: const Text('حفظ المشهد'),
          ),
          _heading('سجل التشغيل'),
          if (activity.isEmpty) const Text('لا توجد أحداث مسجلة بعد', style: TextStyle(color: Colors.white60)),
          ...activity.take(15).map((entry) => ListTile(
            dense: true,
            title: Text(entry['action']?.toString().replaceAll('_', ' ') ?? ''),
            subtitle: Text(entry['at']?.toString() ?? '', textDirection: TextDirection.ltr),
          )),
          const SizedBox(height: 12),
          const Text('التنبيهات داخل التطبيق والسيرفر. إشعارات النظام وقت إغلاق التطبيق تحتاج خدمة إشعارات إضافية.',
            style: TextStyle(color: Colors.white54, fontSize: 11)),
        ],
      ),
    );
  }
}
