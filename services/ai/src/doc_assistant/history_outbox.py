"""Keep history writes off the response path and retry failures in the background."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class HistoryWriter(Protocol):
    def record(
        self, request_id: str, conversation_id: str, created_at: str, trace: dict[str, Any]
    ) -> None: ...


@dataclass(order=True)
class _Entry:
    due: float
    sequence: int
    request_id: str = field(compare=False)
    conversation_id: str = field(compare=False)
    created_at: str = field(compare=False)
    trace: dict[str, Any] = field(compare=False)
    attempts: int = field(default=0, compare=False)


class HistoryOutbox:
    """A process-local retry queue; pending writes do not survive a process restart."""

    def __init__(self, store: HistoryWriter, *, retry_base: float = 1.0) -> None:
        self._store = store
        self._retry_base = retry_base
        self._queue: queue.PriorityQueue[_Entry] = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._failures: deque[dict[str, str]] = deque(maxlen=20)
        self._pending = 0
        self._sequence = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="history-outbox", daemon=True)
        self._thread.start()

    def submit(
        self, request_id: str, conversation_id: str, created_at: str, trace: dict[str, Any]
    ) -> None:
        with self._lock:
            self._sequence += 1
            self._pending += 1
            entry = _Entry(
                time.monotonic(), self._sequence, request_id, conversation_id, created_at, trace
            )
        self._queue.put(entry)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"pending": self._pending, "failures": list(self._failures)}

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                entry = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            delay = entry.due - time.monotonic()
            if delay > 0:
                self._queue.put(entry)
                self._stop.wait(min(delay, 0.1))
                continue
            try:
                self._store.record(
                    entry.request_id, entry.conversation_id, entry.created_at, entry.trace
                )
            except Exception as exc:
                logger.error(
                    "History write failed for request_id=%s (%s)",
                    entry.request_id,
                    type(exc).__name__,
                )
                with self._lock:
                    self._failures.append(
                        {"request_id": entry.request_id, "error": type(exc).__name__}
                    )
                entry.attempts += 1
                entry.due = time.monotonic() + min(
                    self._retry_base * 2 ** min(entry.attempts - 1, 10), 60
                )
                self._queue.put(entry)
            else:
                with self._lock:
                    self._pending -= 1
