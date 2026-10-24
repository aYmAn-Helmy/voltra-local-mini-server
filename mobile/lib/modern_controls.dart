import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Tactile animated surface for actions backed by real Voltra API operations.
class ModernPressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final BorderRadius radius;
  final String? semanticLabel;
  const ModernPressable({
    super.key,
    required this.child,
    required this.onTap,
    this.radius = const BorderRadius.all(Radius.circular(22)),
    this.semanticLabel,
  });

  @override
  State<ModernPressable> createState() => _ModernPressableState();
}

class _ModernPressableState extends State<ModernPressable> {
  bool pressed = false;
  void update(bool next) {
    if (pressed != next && mounted) setState(() => pressed = next);
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;
    return Semantics(
      button: true,
      enabled: enabled,
      label: widget.semanticLabel,
      child: AnimatedScale(
        scale: enabled && pressed ? .965 : 1,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOutCubic,
        child: Material(
          color: Colors.transparent,
          clipBehavior: Clip.antiAlias,
          borderRadius: widget.radius,
          child: InkWell(
            borderRadius: widget.radius,
            splashColor: const Color(0x4443EBA0),
            highlightColor: const Color(0x2236D989),
            onTapDown: enabled ? (_) => update(true) : null,
            onTapCancel: () => update(false),
            onTapUp: enabled ? (_) => update(false) : null,
            onTap: enabled ? () {
              HapticFeedback.selectionClick();
              widget.onTap?.call();
            } : null,
            child: widget.child,
          ),
        ),
      ),
    );
  }
}

/// Distinct idle, on, pending and unavailable animations; no simulated relays.
class ModernOutletTile extends StatelessWidget {
  final int channel;
  final String name;
  final bool on;
  final bool online;
  final bool busy;
  final double powerW;
  final ValueChanged<bool> onChanged;
  const ModernOutletTile({
    super.key,
    required this.channel,
    required this.name,
    required this.on,
    required this.online,
    required this.busy,
    required this.powerW,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    const green = Color(0xFF42E59C);
    const muted = Color(0xFF9CA7B8);
    final accent = on ? green : muted;
    final canToggle = online && !busy;
    final status = busy ? 'Switching' : !online ? 'Unavailable' : on ? 'ON' : 'OFF';
    return ModernPressable(
      semanticLabel: name,
      onTap: canToggle ? () => onChanged(!on) : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeInOutCubic,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: LinearGradient(
            begin: Alignment.topLeft, end: Alignment.bottomRight,
            colors: on
                ? const [Color(0xFF174535), Color(0xFF0E2B28)]
                : const [Color(0xFF1B2536), Color(0xFF121D2E)],
          ),
          border: Border.all(
            color: busy ? const Color(0xFFF2C36F)
                : on ? const Color(0xFF398A67) : const Color(0xFF293547),
            width: on ? 1.5 : 1,
          ),
          boxShadow: on
              ? [BoxShadow(color: green.withValues(alpha: .07),
                  blurRadius: 18, offset: const Offset(0, 5))]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 260),
                  width: 44, height: 44,
                  decoration: BoxDecoration(
                    color: on ? const Color(0xFF24654E) : const Color(0xFF273244),
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 180),
                    child: busy
                        ? const Padding(
                            key: ValueKey('pending'),
                            padding: EdgeInsets.all(11),
                            child: CircularProgressIndicator(strokeWidth: 2.4,
                                color: Color(0xFFF2C36F)),
                          )
                        : Icon(
                            key: ValueKey(on),
                            on ? Icons.power_rounded : Icons.power_settings_new_rounded,
                            size: 26, color: accent,
                          ),
                  ),
                ),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 220),
                  width: 47, height: 26,
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: on ? green : const Color(0xFF3B4557),
                  ),
                  child: AnimatedAlign(
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOutBack,
                    alignment: on ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      height: 20, width: 20,
                      decoration: const BoxDecoration(color: Colors.white,
                          shape: BoxShape.circle),
                    ),
                  ),
                ),
              ],
            ),
            const Spacer(),
            Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
            const SizedBox(height: 7),
            Row(
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 220),
                  width: 6, height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: busy ? const Color(0xFFF2C36F) : accent,
                  ),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 180),
                    child: Text(
                      key: ValueKey(status),
                      busy ? 'Switching…'
                          : on ? 'ON · ${powerW.toStringAsFixed(1)} W' : status,
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: busy ? const Color(0xFFF2C36F) : accent,
                        fontSize: 10, fontWeight: FontWeight.w800,
                      ),
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
