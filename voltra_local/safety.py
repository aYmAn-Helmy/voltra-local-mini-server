"""Software warning monitor (not an electrical safety device).

Protection is opt-in, triggered only by two *distinct*, fresh measurements.
Hardware fuses and certified overload protection remain essential.
"""
from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
from typing import Callable


def is_fresh(value: str | None, max_age_s: float = 90.0) -> bool:
    if not value:
        return False
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        return -10 <= age <= max_age_s
    except (ValueError, TypeError):
        return False


def warning_candidates(strip: dict, settings: dict) -> dict[tuple[str, int], dict]:
    """Only use fresh physical telemetry; never derive measured amps from watts."""
    if not strip.get("online"):
        return {}
    alerts = {}
    mac = str(strip.get("mac") or "").upper()
    info_fresh = is_fresh(strip.get("last_info_at"))
    diagnostics_fresh = is_fresh(strip.get("last_diagnostics_at"))
    current_fresh = is_fresh(strip.get("last_current_at"))
    def add(kind, channel, value, limit, stamp):
        key = (kind, channel)
        alerts[key] = {"mac": mac, "kind": kind, "outlet": channel,
                       "value": round(float(value), 3), "threshold": float(limit),
                       "sample_at": stamp}

    power = sum(float(o.get("power_w") or 0) for o in strip.get("outlets") or [])
    max_power = float(settings.get("alert_max_total_power_w", 3000))
    if info_fresh and power > max_power:
        add("high_power", 0, power, max_power, strip["last_info_at"])

    max_temp = float(settings.get("alert_max_temperature_c", 75))
    if info_fresh:
        for outlet in strip.get("outlets") or []:
            val = outlet.get("temperature_c")
            channel = outlet.get("channel")
            if channel in (1, 2, 3, 4) and isinstance(val, (int, float)) and val > max_temp:
                add("high_temperature", channel, val, max_temp, strip["last_info_at"])

    current = strip.get("total_current_a")
    limit = float(settings.get("alert_max_total_current_a", 12))
    if current_fresh and isinstance(current, (int, float)) and current > limit:
        add("high_current", 0, current, limit, strip["last_current_at"])

    volts = strip.get("voltage_v")
    if diagnostics_fresh and isinstance(volts, (int, float)):
        lo = float(settings.get("voltage_min_v", 200))
        hi = float(settings.get("voltage_max_v", 250))
        if volts < lo:
            add("voltage_low", 0, volts, lo, strip["last_diagnostics_at"])
        if volts > hi:
            add("voltage_high", 0, volts, hi, strip["last_diagnostics_at"])
    return alerts


class SafetyMonitor:
    def __init__(self, *, snapshot_provider: Callable[[], list[dict]],
                 settings_provider: Callable[[], dict],
                 command_executor: Callable[[str, int, bool], dict],
                 event_bus=None, audit=None, interval: float = 5):
        self.snapshot_provider = snapshot_provider
        self.settings_provider = settings_provider
        self.command_executor = command_executor
        self.event_bus = event_bus
        self.audit = audit
        self.interval = max(1.0, float(interval))
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self._alerts: dict[tuple[str, str, int], dict] = {}
        self._samples: dict[tuple[str, str, int], tuple[str, int]] = {}
        self._acted: set[tuple[str, str, int]] = set()

    def active(self) -> list[dict]:
        with self._lock:
            return [dict(v) for v in self._alerts.values()]

    def evaluate(self, devices: list[dict]) -> None:
        settings = self.settings_provider()
        candidates: dict[tuple[str, str, int], dict] = {}
        for strip in devices:
            if not strip.get("managed") or strip.get("state") != "active" or not strip.get("enabled"):
                continue
            for (kind, outlet), entry in warning_candidates(strip, settings).items():
                candidates[(entry["mac"], kind, outlet)] = entry
        actions: list[tuple[str, tuple[str, str, int]]] = []
        with self._lock:
            for key in set(self._alerts) - set(candidates):
                event = self._alerts.pop(key)
                self._acted.discard(key)
                self._samples.pop(key, None)
                if self.event_bus:
                    self.event_bus.publish("safety_alert_cleared", **event)
            for key, event in candidates.items():
                last_at, count = self._samples.get(key, ("", 0))
                if last_at != event["sample_at"]:
                    count = min(2, count + 1)
                self._samples[key] = (event["sample_at"], count)
                if count < 2:
                    continue
                if key not in self._alerts:
                    self._alerts[key] = dict(event)
                    if self.event_bus:
                        self.event_bus.publish("safety_alert_raised", **event)
                    if self.audit:
                        self.audit.append("safety", "alert_raised", **event)
                else:
                    self._alerts[key] = dict(event)
                if settings.get("alert_auto_off_enabled", False) and key not in self._acted:
                    # Trip the whole strip only for over-power/current/temperature.
                    # A software command is not guaranteed to execute.
                    if event["kind"] in {"high_power", "high_current", "high_temperature"}:
                        self._acted.add(key)
                        actions.append((event["mac"], key))
        for mac, key in actions:
            for channel in (1, 2, 3, 4):
                try:
                    self.command_executor(mac, channel, False)
                except Exception as exc:
                    if self.audit:
                        self.audit.append("safety", "shutdown_failed",
                                          mac=mac, channel=channel, error=str(exc))
            if self.event_bus:
                self.event_bus.publish("safety_shutdown_attempted", mac=mac, reason=key[1])

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.evaluate(self.snapshot_provider())
            except Exception as exc:
                if self.audit:
                    self.audit.append("safety", "monitor_error", error=str(exc))
            self._stop.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
