from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
from typing import Callable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TelemetryStore:
    def __init__(self, path: str | os.PathLike[str], sample_interval: float = 60.0):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sample_interval = max(5.0, float(sample_interval))
        self._provider: Callable[[], list[dict]] | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def start(self, provider: Callable[[], list[dict]]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._provider = provider
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="voltra-telemetry")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        self.record(self._provider() if self._provider else [])
        while not self._stop.wait(self.sample_interval):
            try:
                self.record(self._provider() if self._provider else [])
            except Exception as exc:
                print(f"[TELEMETRY] sample failed: {exc}")

    def record(self, devices: list[dict]) -> None:
        now = utc_now()
        lines = []
        for device in devices:
            mac = device.get("mac")
            if not mac:
                continue
            outlets = device.get("outlets") or []
            lines.append({
                "at": now,
                "mac": str(mac),
                "voltage_v": device.get("voltage_v"),
                "wifi_rssi_dbm": device.get("wifi_rssi_dbm"),
                "total_power_w": round(sum(float(x.get("power_w") or 0) for x in outlets), 3),
                "energy_kwh": round(sum(float(x.get("energy_kwh") or 0) for x in outlets), 6),
                "outlets": [
                    {
                        "channel": x.get("channel"),
                        "power_w": x.get("power_w"),
                        "energy_kwh": x.get("energy_kwh"),
                        "relay": x.get("relay"),
                    }
                    for x in outlets
                ],
            })
        if not lines:
            return
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            for item in lines:
                handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    def history(self, mac: str, hours: float = 24.0, limit: int = 96) -> dict:
        hours = max(0.25, min(float(hours), 24.0 * 365))
        limit = max(12, min(int(limit), 500))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = []

        if self.path.exists():
            with self._lock:
                try:
                    lines = self.path.read_text(encoding="utf-8").splitlines()
                except OSError:
                    lines = []

            for line in lines:
                try:
                    item = json.loads(line)
                    at = datetime.fromisoformat(str(item.get("at")))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
                if str(item.get("mac", "")).upper() == mac.upper() and at >= cutoff:
                    rows.append(item)

        if len(rows) > limit:
            step = max(1, len(rows) // limit)
            sampled = rows[::step]
            if sampled[-1] is not rows[-1]:
                sampled.append(rows[-1])
            rows = sampled[-limit:]

        points = [
            {
                "at": row.get("at"),
                "power_w": round(float(row.get("total_power_w") or 0), 3),
                "energy_kwh": round(float(row.get("energy_kwh") or 0), 6),
                "voltage_v": row.get("voltage_v"),
                "wifi_rssi_dbm": row.get("wifi_rssi_dbm"),
            }
            for row in rows
        ]

        return {
            "mac": mac.upper(),
            "hours": hours,
            "samples": len(points),
            "points": points,
        }

    def summary(self, mac: str, hours: float = 24.0) -> dict:
        hours = max(0.25, min(float(hours), 24.0 * 365))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = []
        if self.path.exists():
            with self._lock:
                try:
                    lines = self.path.read_text(encoding="utf-8").splitlines()
                except OSError:
                    lines = []
            for line in lines:
                try:
                    item = json.loads(line)
                    at = datetime.fromisoformat(str(item.get("at")))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
                if str(item.get("mac", "")).upper() == mac.upper() and at >= cutoff:
                    rows.append(item)
        powers = [float(x.get("total_power_w") or 0) for x in rows]
        energy_delta = 0.0
        if len(rows) >= 2:
            energy_delta = max(0.0, float(rows[-1].get("energy_kwh") or 0) - float(rows[0].get("energy_kwh") or 0))
        return {
            "mac": mac.upper(),
            "hours": hours,
            "samples": len(rows),
            "energy_kwh": round(energy_delta, 6),
            "average_power_w": round(sum(powers) / len(powers), 3) if powers else 0.0,
            "max_power_w": round(max(powers), 3) if powers else 0.0,
            "first": rows[0] if rows else None,
            "latest": rows[-1] if rows else None,
        }
