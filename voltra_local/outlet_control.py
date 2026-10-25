from __future__ import annotations

"""Shared, server-enforced controls for HTTP, scenes and automation."""

from typing import Any


class OutletManager:
    def __init__(self, store, mttl, *, audit=None, event_bus=None):
        self.store = store
        self.mttl = mttl
        self.audit = audit
        self.event_bus = event_bus
        self.automation = None

    def bind_automation(self, automation) -> None:
        self.automation = automation

    def _emit(self, kind: str, mac: str, outlet: int, **details) -> None:
        prefs = self.store.outlet_preferences(mac, outlet)
        if self.audit:
            self.audit.append("outlet", kind, mac=mac, outlet=outlet, **details)
        if self.event_bus and prefs.get("notify", True):
            self.event_bus.publish("outlet_activity", action=kind, mac=mac, outlet=outlet, **details)

    def _managed_key(self, mac: str, outlet: int, kind: str) -> str:
        return f"outlet:{self.store.normalize_mac(mac)}:{outlet}:{kind}"

    def _cancel_auto_off(self, mac: str, outlet: int) -> None:
        if self.automation:
            self.automation.delete_managed_schedules(self._managed_key(mac, outlet, "auto_off"))

    def _arm_auto_off(self, mac: str, outlet: int, prefs: dict) -> None:
        self._cancel_auto_off(mac, outlet)
        minutes = prefs.get("auto_off_minutes") or 0
        if self.automation and minutes:
            self.automation.create_countdown({
                "mac": mac, "outlet": outlet, "on": False,
                "delay_seconds": int(minutes) * 60,
                "offline_policy": "skip",
                "managed_key": self._managed_key(mac, outlet, "auto_off"),
            })

    def command(self, mac: str, outlet: int, on: bool, *, source: str = "manual",
                confirmed: bool = False) -> dict:
        mac = self.store.normalize_mac(mac)
        prefs = self.store.authorize_outlet(mac, outlet, on,
                                            confirmed=confirmed, automation=source != "manual")
        result = self.mttl.get(mac).set_outlet(outlet, on)
        verified = result.get("metrics", {}).get("last_command_confirmed") is True
        self._emit("power_on" if on else "power_off", mac, outlet,
                   on=on, source=source, verified=verified)
        if verified:
            self.store.remember_relay(mac, outlet, on)
            if on:
                self._arm_auto_off(mac, outlet, prefs)
            else:
                self._cancel_auto_off(mac, outlet)
        return result

    def preferences(self, mac: str, outlet: int, updates: dict[str, Any]) -> dict:
        self.store.require_strip_controllable(mac)
        prefs = self.store.set_outlet_preferences(mac, outlet, updates)
        if self.automation:
            for kind in ("low_power", "high_power"):
                self.automation.delete_managed_rules(self._managed_key(mac, outlet, kind))
            if prefs["low_power_enabled"]:
                self.automation.create_rule({
                    "mac": mac, "outlet": outlet, "condition": "low_power",
                    "threshold": prefs["low_power_threshold_w"],
                    "duration_s": prefs["low_power_duration_s"],
                    "cooldown_s": 3600,
                    "action": {"type": "set_outlet", "outlet": outlet, "on": False},
                    "managed_key": self._managed_key(mac, outlet, "low_power"),
                })
            if prefs["alert_above_w"] > 0:
                self.automation.create_rule({
                    "mac": mac, "outlet": outlet, "condition": "high_power",
                    "threshold": prefs["alert_above_w"],
                    "duration_s": 10, "cooldown_s": 600,
                    "action": {"type": "audit"},
                    "managed_key": self._managed_key(mac, outlet, "high_power"),
                })
        current = self._current_relay(mac, outlet)
        if current is True and "auto_off_minutes" in updates:
            self._arm_auto_off(mac, outlet, prefs)
        self._emit("preferences_changed", self.store.normalize_mac(mac), outlet,
                   fields=list(updates))
        return prefs

    def _current_relay(self, mac: str, outlet: int) -> bool | None:
        try:
            snapshot = self.mttl.get(mac).snapshot()
        except (KeyError, RuntimeError):
            return None
        return next((x.get("relay") for x in snapshot.get("outlets", [])
                     if x.get("channel") == outlet), None)

    def on_device_ready(self, session) -> None:
        """Opt-in reconnect policy, only after a valid GETINFO reply."""
        mac = session.mac
        if not mac or not self.store.strip_controllable(mac):
            return
        for outlet in (1, 2, 3, 4):
            prefs = self.store.outlet_preferences(mac, outlet)
            policy = prefs.get("restore_policy")
            if policy == "none":
                continue
            target = False if policy == "off" else prefs.get("last_relay")
            if not isinstance(target, bool) or self._current_relay(mac, outlet) is target:
                continue
            try:
                self.command(mac, outlet, target, source="restore")
            except Exception as exc:
                self._emit("restore_skipped", mac, outlet, reason=str(exc))

    def activity(self, mac: str, outlet: int, limit: int = 30) -> list[dict]:
        if not self.audit:
            return []
        mac = self.store.normalize_mac(mac)
        self.store.outlet_preferences(mac, outlet)
        events = self.audit.recent(1000)
        selected = []
        for event in reversed(events):
            info = event.get("details") or {}
            if info.get("mac") == mac and info.get("outlet") == outlet:
                selected.append(event)
                if len(selected) >= min(100, max(1, limit)):
                    break
        return selected
