"""Non-actuating, configurable health alerts for stock MTTL-W01 strips."""
from __future__ import annotations

import threading
from datetime import datetime, timezone


def inspect_snapshot(strip: dict, *, max_power_w: float = 1500.0,
                     max_temp_c: float = 75.0, max_current_a: float = 12.0) -> list[dict]:
    """Report warnings; never mistake these for hardware overcurrent protection."""
    alerts: list[dict] = []
    mac = strip.get("mac")
    if not mac or not strip.get("online", True):
        return alerts
    outlets = strip.get("outlets") or []
    power = sum(float(o.get("power_w") or 0) for o in outlets)
    if power > max_power_w:
        alerts.append({"mac": mac, "code": "high_power", "value": round(power, 2), "threshold": max_power_w})
    current = strip.get("total_current_a")
    if isinstance(current, (int, float)) and current > max_current_a:
        alerts.append({"mac": mac, "code": "high_current", "value": round(current, 3), "threshold": max_current_a})
    for outlet in outlets:
        temp = outlet.get("temperature_c")
        if isinstance(temp, (int, float)) and temp > max_temp_c:
            alerts.append({"mac": mac, "code": "high_temperature", "channel": outlet.get("channel"),
                           "value": temp, "threshold": max_temp_c})
        if outlet.get("overload_protection") or outlet.get("overheat_protection"):
            alerts.append({"mac": mac, "code": "device_protection_reported", "channel": outlet.get("channel")})
    return alerts


class AlertMonitor:
    def __init__(self, snapshot_provider, event_bus, audit, *,
                 settings_provider=None, interval=10.0):
        self.snapshot_provider = snapshot_provider
        self.settings_provider = settings_provider
        self.event_bus = event_bus
        self.audit = audit
        self.interval = max(float(interval), 2.0)
        self._seen: set[tuple] = set()
        self._stop = threading.Event()
        self._thread = None

    def scan(self):
        settings = self.settings_provider() if self.settings_provider else {}
        power = float(settings.get("unusual_power_w") or 1500)
        current = float(settings.get("alert_current_a") or 12)
        temp = float(settings.get("alert_temperature_c") or 75)
        active = []
        for strip in self.snapshot_provider():
            active.extend(inspect_snapshot(strip, max_power_w=power,
                                           max_current_a=current, max_temp_c=temp))
        seen = {(a["mac"], a["code"], a.get("channel")) for a in active}
        for alert in active:
            key = alert["mac"], alert["code"], alert.get("channel")
            if key not in self._seen:
                alert["at"] = datetime.now(timezone.utc).isoformat()
                if self.event_bus:
                    self.event_bus.publish("device_alert", **alert)
                if self.audit:
                    self.audit.append("device", "device_alert", **alert)
        self._seen = seen
        return active

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="voltra-alerts")
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.scan()
            except Exception as exc:
                print(f"[ALERTS] scan failed: {exc}")
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
