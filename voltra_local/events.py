from __future__ import annotations

from datetime import datetime, timezone
import queue
import threading


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventBus:
    """Small in-process fan-out bus used by SSE and internal services."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: set[queue.Queue] = set()
        self._sequence = 0

    def publish(self, kind: str, **payload) -> dict:
        with self._lock:
            self._sequence += 1
            event = {
                "id": self._sequence,
                "type": str(kind),
                "at": utc_now(),
                "data": payload,
            }
            subscribers = list(self._subscribers)
        for target in subscribers:
            try:
                target.put_nowait(event)
            except queue.Full:
                try:
                    target.get_nowait()
                    target.put_nowait(event)
                except (queue.Empty, queue.Full):
                    pass
        return event

    def subscribe(self, maxsize: int = 100) -> queue.Queue:
        target: queue.Queue = queue.Queue(maxsize=maxsize)
        with self._lock:
            self._subscribers.add(target)
        return target

    def unsubscribe(self, target: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(target)
