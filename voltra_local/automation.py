from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Callable
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutomationEngine:
    """Schedules, offline command queue, and lightweight automation rules."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        snapshot_provider: Callable[[], list[dict]],
        command_executor: Callable[[str, int, bool, str], dict],
        *,
        audit=None,
        event_bus=None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_provider = snapshot_provider
        self.command_executor = command_executor
        self.audit = audit
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._rule_state: dict[str, dict] = {}
        self._data = self._load()

    def _default(self) -> dict:
        return {"version": 1, "schedules": {}, "rules": {}, "queue": []}

    def _load(self) -> dict:
        if not self.path.exists():
            return self._default()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._default()
        if not isinstance(value, dict):
            return self._default()
        base = self._default()
        base["schedules"] = value.get("schedules") if isinstance(value.get("schedules"), dict) else {}
        base["rules"] = value.get("rules") if isinstance(value.get("rules"), dict) else {}
        base["queue"] = value.get("queue") if isinstance(value.get("queue"), list) else []
        return base

    def _save_locked(self) -> None:
        fd, tmp = tempfile.mkstemp(prefix="automation-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="voltra-automation")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict:
        with self._lock:
            return json.loads(json.dumps(self._data))

    def import_data(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("automation backup must be an object")
        schedules = value.get("schedules", {})
        rules = value.get("rules", {})
        queue = value.get("queue", [])
        if not isinstance(schedules, dict) or not isinstance(rules, dict) or not isinstance(queue, list):
            raise ValueError("invalid automation backup")
        with self._lock:
            self._data = {"version": 1, "schedules": schedules, "rules": rules, "queue": queue}
            self._save_locked()

    def create_schedule(self, value: dict) -> dict:
        mac = self._clean_mac(value.get("mac"))
        outlet = self._clean_outlet(value.get("outlet"))
        on = value.get("on")
        if not isinstance(on, bool):
            raise ValueError("on must be boolean")

        offline_policy = str(value.get("offline_policy") or "queue")
        if offline_policy not in {"queue", "skip"}:
            raise ValueError("offline_policy must be queue or skip")

        run_at_raw = str(value.get("run_at") or "").strip()
        if run_at_raw:
            try:
                run_at_dt = datetime.fromisoformat(run_at_raw.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("run_at must be an ISO-8601 datetime")
            if run_at_dt.tzinfo is None:
                run_at_dt = run_at_dt.astimezone()
            run_at = run_at_dt.astimezone(timezone.utc).isoformat()
            at = None
            days = []
            schedule_type = "once"
        else:
            at = str(value.get("time") or "").strip()
            self._parse_time(at)
            days = value.get("days", list(range(7)))
            if not isinstance(days, list) or not days or any((not isinstance(x, int) or x < 0 or x > 6) for x in days):
                raise ValueError("days must contain weekday numbers 0..6")
            days = sorted(set(days))
            run_at = None
            schedule_type = "recurring"

        item = {
            "id": uuid4().hex,
            "mac": mac,
            "outlet": outlet,
            "on": on,
            "type": schedule_type,
            "time": at,
            "days": days,
            "run_at": run_at,
            "enabled": bool(value.get("enabled", True)),
            "offline_policy": offline_policy,
            "max_queue_age_minutes": max(1, min(int(value.get("max_queue_age_minutes") or 360), 10080)),
            "created_at": utc_now(),
            "last_run_key": None,
        }
        with self._lock:
            self._data["schedules"][item["id"]] = item
            self._save_locked()
        self._event("schedule_created", item=item)
        return dict(item)

    def create_countdown(self, value: dict) -> dict:
        try:
            delay_seconds = int(value.get("delay_seconds"))
        except (TypeError, ValueError):
            raise ValueError("delay_seconds must be an integer")
        delay_seconds = max(1, min(delay_seconds, 30 * 24 * 60 * 60))
        run_at = datetime.now(timezone.utc).timestamp() + delay_seconds
        payload = dict(value)
        payload["run_at"] = datetime.fromtimestamp(run_at, timezone.utc).isoformat()
        payload.pop("delay_seconds", None)
        item = self.create_schedule(payload)
        item["delay_seconds"] = delay_seconds
        return item

    def delete_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            existed = self._data["schedules"].pop(schedule_id, None) is not None
            if existed:
                self._save_locked()
        if existed:
            self._event("schedule_deleted", schedule_id=schedule_id)
        return existed

    def create_rule(self, value: dict) -> dict:
        kind = str(value.get("condition") or "").strip()
        if kind not in {"offline", "weak_wifi", "low_power", "voltage_below", "voltage_above"}:
            raise ValueError("unsupported rule condition")
        mac = self._clean_mac(value.get("mac"))
        outlet = value.get("outlet")
        if outlet is not None:
            outlet = self._clean_outlet(outlet)
        threshold = value.get("threshold")
        if kind != "offline":
            if not isinstance(threshold, (int, float)):
                raise ValueError("threshold must be numeric")
            threshold = float(threshold)
        action = value.get("action") or {"type": "audit"}
        if not isinstance(action, dict):
            raise ValueError("action must be an object")
        action_type = str(action.get("type") or "audit")
        if action_type not in {"audit", "set_outlet"}:
            raise ValueError("action type must be audit or set_outlet")
        clean_action = {"type": action_type}
        if action_type == "set_outlet":
            clean_action["outlet"] = self._clean_outlet(action.get("outlet"))
            if not isinstance(action.get("on"), bool):
                raise ValueError("action.on must be boolean")
            clean_action["on"] = action["on"]
        item = {
            "id": uuid4().hex,
            "mac": mac,
            "outlet": outlet,
            "condition": kind,
            "threshold": threshold,
            "duration_s": max(0.0, min(float(value.get("duration_s") or 0), 86400.0)),
            "cooldown_s": max(1.0, min(float(value.get("cooldown_s") or 300), 86400.0)),
            "action": clean_action,
            "enabled": bool(value.get("enabled", True)),
            "created_at": utc_now(),
        }
        with self._lock:
            self._data["rules"][item["id"]] = item
            self._save_locked()
        self._event("rule_created", item=item)
        return dict(item)

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            existed = self._data["rules"].pop(rule_id, None) is not None
            self._rule_state.pop(rule_id, None)
            if existed:
                self._save_locked()
        if existed:
            self._event("rule_deleted", rule_id=rule_id)
        return existed

    def clear_queue(self) -> int:
        with self._lock:
            count = len(self._data["queue"])
            self._data["queue"] = []
            self._save_locked()
        self._event("queue_cleared", count=count)
        return count

    def _loop(self) -> None:
        last_rules = 0.0
        while not self._stop.wait(1.0):
            try:
                snapshots = self.snapshot_provider()
                self._run_schedules(snapshots)
                self._drain_queue(snapshots)
                now = time.monotonic()
                if now - last_rules >= 5.0:
                    self._run_rules(snapshots, now)
                    last_rules = now
            except Exception as exc:
                print(f"[AUTOMATION] tick failed: {exc}")

    def _run_schedules(self, snapshots: list[dict]) -> None:
        local_now = datetime.now().astimezone()
        utc_now_dt = datetime.now(timezone.utc)
        run_key = local_now.strftime("%Y-%m-%dT%H:%M")
        clock = local_now.strftime("%H:%M")
        weekday = local_now.weekday()
        changed = False
        with self._lock:
            schedules = list(self._data["schedules"].values())

        for item in schedules:
            if not item.get("enabled"):
                continue

            is_once = str(item.get("type") or "") == "once" or bool(item.get("run_at"))
            if is_once:
                if item.get("last_run_at"):
                    continue
                try:
                    target = datetime.fromisoformat(str(item.get("run_at")).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
                if target.tzinfo is None:
                    target = target.astimezone()
                if utc_now_dt < target.astimezone(timezone.utc):
                    continue
                schedule_run_key = f"once:{item['id']}"
            else:
                if item.get("time") != clock or weekday not in item.get("days", []):
                    continue
                if item.get("last_run_key") == run_key:
                    continue
                schedule_run_key = run_key

            self._execute_or_queue(
                item["mac"],
                int(item["outlet"]),
                bool(item["on"]),
                source=f"schedule:{item['id']}",
                offline_policy=str(item.get("offline_policy") or "queue"),
                max_queue_age_minutes=int(item.get("max_queue_age_minutes") or 360),
                snapshots=snapshots,
            )
            with self._lock:
                live = self._data["schedules"].get(item["id"])
                if live:
                    live["last_run_key"] = schedule_run_key
                    live["last_run_at"] = utc_now()
                    if is_once:
                        live["enabled"] = False
                    changed = True

        if changed:
            with self._lock:
                self._save_locked()

    def _execute_or_queue(
        self,
        mac: str,
        outlet: int,
        on: bool,
        *,
        source: str,
        offline_policy: str,
        max_queue_age_minutes: int,
        snapshots: list[dict],
    ) -> None:
        online = any(str(x.get("mac") or "").upper() == mac and x.get("online", True) for x in snapshots)
        if online:
            try:
                self.command_executor(mac, outlet, on, source)
                self._event("automation_executed", mac=mac, outlet=outlet, on=on, source=source)
                return
            except (KeyError, RuntimeError, TimeoutError):
                online = False
        if offline_policy == "queue":
            queued = {
                "id": uuid4().hex,
                "mac": mac,
                "outlet": outlet,
                "on": on,
                "source": source,
                "queued_at": utc_now(),
                "expires_at_epoch": time.time() + max_queue_age_minutes * 60,
            }
            with self._lock:
                self._data["queue"].append(queued)
                self._save_locked()
            self._event("command_queued", item=queued)
        else:
            self._audit("automation", "command_skipped_offline", mac=mac, outlet=outlet, on=on, source=source)

    def _drain_queue(self, snapshots: list[dict]) -> None:
        online = {str(x.get("mac") or "").upper() for x in snapshots if x.get("online", True)}
        now = time.time()
        changed = False
        with self._lock:
            items = list(self._data["queue"])
        for item in items:
            remove = False
            if float(item.get("expires_at_epoch") or 0) < now:
                self._audit("automation", "queued_command_expired", **item)
                remove = True
            elif item.get("mac") in online:
                try:
                    self.command_executor(item["mac"], int(item["outlet"]), bool(item["on"]), str(item.get("source") or "queue"))
                    self._event("queued_command_executed", item=item)
                    remove = True
                except Exception:
                    pass
            if remove:
                with self._lock:
                    self._data["queue"] = [x for x in self._data["queue"] if x.get("id") != item.get("id")]
                    changed = True
        if changed:
            with self._lock:
                self._save_locked()

    def _run_rules(self, snapshots: list[dict], monotonic_now: float) -> None:
        by_mac = {str(x.get("mac") or "").upper(): x for x in snapshots}
        with self._lock:
            rules = list(self._data["rules"].values())
        for rule in rules:
            rule_id = rule["id"]
            if not rule.get("enabled"):
                self._rule_state.pop(rule_id, None)
                continue
            matched = self._rule_matches(rule, by_mac.get(rule["mac"]))
            state = self._rule_state.setdefault(rule_id, {"since": None, "last_fired": 0.0})
            if not matched:
                state["since"] = None
                continue
            if state["since"] is None:
                state["since"] = monotonic_now
            if monotonic_now - state["since"] < float(rule.get("duration_s") or 0):
                continue
            if monotonic_now - float(state.get("last_fired") or 0) < float(rule.get("cooldown_s") or 300):
                continue
            self._fire_rule(rule)
            state["last_fired"] = monotonic_now

    def _rule_matches(self, rule: dict, snapshot: dict | None) -> bool:
        kind = rule["condition"]
        if kind == "offline":
            return snapshot is None or not snapshot.get("online", True)
        if snapshot is None:
            return False
        threshold = float(rule.get("threshold") or 0)
        if kind == "weak_wifi":
            value = snapshot.get("wifi_rssi_dbm")
            return isinstance(value, (int, float)) and float(value) <= threshold
        if kind in {"voltage_below", "voltage_above"}:
            value = snapshot.get("voltage_v")
            if not isinstance(value, (int, float)):
                return False
            return float(value) < threshold if kind == "voltage_below" else float(value) > threshold
        if kind == "low_power":
            outlets = snapshot.get("outlets") or []
            outlet = rule.get("outlet")
            if outlet is None:
                value = sum(float(x.get("power_w") or 0) for x in outlets)
            else:
                row = next((x for x in outlets if int(x.get("channel") or 0) == int(outlet)), None)
                if row is None:
                    return False
                value = float(row.get("power_w") or 0)
            return value <= threshold
        return False

    def _fire_rule(self, rule: dict) -> None:
        action = rule.get("action") or {"type": "audit"}
        if action.get("type") == "set_outlet":
            try:
                self.command_executor(
                    rule["mac"],
                    int(action["outlet"]),
                    bool(action["on"]),
                    f"rule:{rule['id']}",
                )
                outcome = "executed"
            except Exception as exc:
                outcome = f"failed:{exc}"
        else:
            outcome = "audit_only"
        self._audit("automation", "rule_fired", rule_id=rule["id"], mac=rule["mac"], outcome=outcome)
        self._event("rule_fired", rule_id=rule["id"], mac=rule["mac"], outcome=outcome)

    def _event(self, kind: str, **payload) -> None:
        if self.event_bus:
            self.event_bus.publish(kind, **payload)

    def _audit(self, category: str, action: str, **details) -> None:
        if self.audit:
            self.audit.append(category, action, **details)

    @staticmethod
    def _parse_time(value: str) -> tuple[int, int]:
        try:
            hour_s, minute_s = value.split(":", 1)
            hour, minute = int(hour_s), int(minute_s)
        except (ValueError, AttributeError):
            raise ValueError("time must be HH:MM")
        if hour not in range(24) or minute not in range(60):
            raise ValueError("time must be HH:MM")
        return hour, minute

    @staticmethod
    def _clean_outlet(value) -> int:
        try:
            outlet = int(value)
        except (TypeError, ValueError):
            raise ValueError("outlet must be 1..4")
        if outlet not in (1, 2, 3, 4):
            raise ValueError("outlet must be 1..4")
        return outlet

    @staticmethod
    def _clean_mac(value) -> str:
        mac = str(value or "").replace(":", "").replace("-", "").strip().upper()
        if len(mac) != 12 or any(ch not in "0123456789ABCDEF" for ch in mac):
            raise ValueError("invalid MAC address")
        return mac
