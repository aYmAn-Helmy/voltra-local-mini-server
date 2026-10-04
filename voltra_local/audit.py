from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLog:
    def __init__(self, path: str | os.PathLike[str], max_bytes: int = 5 * 1024 * 1024):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max(256 * 1024, int(max_bytes))
        self._lock = threading.RLock()

    def append(self, category: str, action: str, **details) -> dict:
        event = {
            "at": utc_now(),
            "category": str(category),
            "action": str(action),
            "details": details,
        }
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._rotate_locked()
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return event

    def recent(self, limit: int = 100) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        if not self.path.exists():
            return []
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
            except OSError:
                return []
        result = []
        for line in lines:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                result.append(value)
        return result

    def _rotate_locked(self) -> None:
        try:
            if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
                return
            previous = self.path.with_suffix(self.path.suffix + ".1")
            if previous.exists():
                previous.unlink()
            os.replace(self.path, previous)
        except OSError:
            pass
