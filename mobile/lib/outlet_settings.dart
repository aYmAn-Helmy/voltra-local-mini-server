import 'package:flutter/material.dart';
import 'app_controller.dart';

const _iconChoices = ['plug', 'tv', 'gamepad', 'router', 'computer', 'light', 'fan', 'other'];

Future<void> openOutletSettings(
  BuildContext context, AppController controller, Map<String, dynamic> strip,
  int channel, Map<String, dynamic>? outlet,
) async {
  final mac = strip['mac']?.toString() ?? '';
  final prefs = Map<String, dynamic>.from(outlet?['preferences'] as Map? ?? {});
  final name = TextEditingController(text: prefs['name']?.toString() ?? '');
  final threshold = TextEditingController(text: '5');
  final duration = TextEditingController(text: '120');
  final timer = TextEditingController(text: '60');
  final scheduleTime = TextEditingController(text: '23:00');
  var icon = _iconChoices.contains(prefs['icon']) ? prefs['icon'].toString() : 'plug';
  var protect = prefs['protected'] == true;
  var locked = prefs['locked'] == true;
  var notifications = prefs['notifications'] == true;
  var on = false;
  var days = <int>{0, 1, 2, 3, 4, 5, 6};
  var busy = false;
  String? feedback;
  try {
    await showModalBottomSheet<void>(
      context: context, isScrollControlled: true, useSafeArea: true,
      builder: (sheetContext) => StatefulBuilder(builder: (ctx, update) {
        Future<void> run(Future<void> Function() action) async {
          if (busy) return;
          update(() { busy = true; feedback = null; });
          try {
            await action();
            if (ctx.mounted) update(() => feedback = 'تم الحفظ بنجاح / Saved');
          } catch (e) {
            if (ctx.mounted) update(() => feedback = e.toString());
          } finally {
            if (ctx.mounted) update(() => busy = false);
          }
        }
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(ctx).bottom),
          child: DraggableScrollableSheet(
            expand: false, initialChildSize: 0.83, maxChildSize: 0.95,
            builder: (_, scroll) => ListView(
              controller: scroll, padding: const EdgeInsets.all(18),
              children: [
                Text('إعدادات المخرج $channel · Outlet settings',
                    textDirection: TextDirection.rtl, style: Theme.of(ctx).textTheme.titleLarge),
                const SizedBox(height: 14),
                TextField(controller: name, maxLength: 80, textDirection: TextDirection.rtl,
                    textAlign: TextAlign.right,
                    decoration: const InputDecoration(labelText: 'اسم المخرج / Outlet name')),
                DropdownButtonFormField<String>(
                  value: icon, decoration: const InputDecoration(labelText: 'الأيقونة / Icon'),
                  items: _iconChoices.map((v) => DropdownMenuItem(value: v, child: Text(v))).toList(),
                  onChanged: busy ? null : (v) => update(() => icon = v ?? 'plug'),
                ),
                SwitchListTile(title: const Text('تأكيد قبل الإيقاف / Protected'),
                  value: protect, onChanged: busy ? null : (v) => update(() => protect = v)),
                SwitchListTile(title: const Text('قفل المخرج / Lock'),
                  value: locked, onChanged: busy ? null : (v) => update(() => locked = v)),
                SwitchListTile(title: const Text('تفضيل التنبيهات / Notifications preference'),
                  value: notifications, onChanged: busy ? null : (v) => update(() => notifications = v)),
                FilledButton(
                  onPressed: busy ? null : () => run(() => controller.saveOutlet(mac, channel, {
                    'name': name.text.trim(), 'icon': icon, 'protected': protect,
                    'locked': locked, 'notifications': notifications, 'restore_policy': 'device',
                  })),
                  child: const Text('حفظ الإعدادات / Save settings'),
                ),
                const Divider(height: 32),
                Text('مؤقت إيقاف / Auto-Off', style: Theme.of(ctx).textTheme.titleMedium),
                TextField(controller: timer, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'بعد كام دقيقة؟ / Minutes')),
                OutlinedButton(onPressed: busy || protect || locked ? null : () => run(() {
                  final minutes = int.tryParse(timer.text);
                  if (minutes == null || minutes < 1 || minutes > 43200) {
                    throw ArgumentError('Minutes must be 1-43200');
                  }
                  return controller.outletCountdown(mac, channel, minutes);
                }), child: const Text('بدء المؤقت / Start timer')),
                const Divider(height: 32),
                Text('جدول أسبوعي / Weekly schedule', style: Theme.of(ctx).textTheme.titleMedium),
                TextField(controller: scheduleTime, decoration: const InputDecoration(labelText: 'HH:MM')),
                SwitchListTile(title: const Text('تشغيل / Turn ON (otherwise OFF)'), value: on,
                    onChanged: (v) => update(() => on = v)),
                Wrap(spacing: 6, children: List.generate(7, (i) => FilterChip(
                  label: Text(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i]),
                  selected: days.contains(i), onSelected: (yes) => update(() =>
                    yes ? days.add(i) : days.remove(i))))),
                OutlinedButton(onPressed: busy || locked || (protect && !on) || days.isEmpty ? null
                    : () => run(() => controller.outletSchedule(mac, channel, on, scheduleTime.text.trim(), days.toList())),
                    child: const Text('حفظ الجدول / Create schedule')),
                const Divider(height: 32),
                Text('إيقاف عند الاستهلاك المنخفض / Low-power auto-off',
                    style: Theme.of(ctx).textTheme.titleMedium),
                TextField(controller: threshold, keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Threshold (W)')),
                TextField(controller: duration, keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Duration (seconds)')),
                OutlinedButton(onPressed: busy || locked || protect ? null : () => run(() {
                  final watts = double.tryParse(threshold.text);
                  final seconds = int.tryParse(duration.text);
                  if (watts == null || watts < 0 || seconds == null || seconds < 10) {
                    throw ArgumentError('Invalid threshold or duration');
                  }
                  return controller.outletLowPower(mac, channel, watts, seconds);
                }), child: const Text('إنشاء قاعدة / Create automation')),
                const SizedBox(height: 10),
                const Text('سياسة استرجاع الكهرباء يتحكم بها Firmware المشترك. القفل والحماية تمنع أوامر الإيقاف التلقائية.'),
                if (feedback != null) Text(feedback!, textDirection: TextDirection.rtl),
                const SizedBox(height: 25),
              ],
            ),
          ),
        );
      }),
    );
  } finally {
    name.dispose(); threshold.dispose(); duration.dispose(); timer.dispose(); scheduleTime.dispose();
  }
}
