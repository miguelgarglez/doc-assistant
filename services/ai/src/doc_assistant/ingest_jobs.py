"""Progress of uploads being processed, so the client can show each stage as it happens.

The client picks a job id, sends it with the upload, and follows
`GET /ingest/jobs/{id}/events`. Jobs live in memory and expire: a restart loses them,
and the upload response stays the source of truth for the result.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any, Literal

Stage = Literal["received", "reading", "ocr", "extracting", "indexing", "done", "error"]

LABELS: dict[str, str] = {
    "received": "Recibido",
    "reading": "Leyendo el PDF y renderizando páginas",
    "ocr": "Reconociendo el texto de la imagen (OCR)",
    "extracting": "Extrayendo los campos",
    "indexing": "Indexando fragmentos",
    "done": "Listo",
    "error": "Error",
}
TERMINAL = frozenset({"done", "error"})
TTL_S = 900.0
MAX_JOBS = 200


@dataclass(frozen=True)
class JobState:
    stage: Stage
    label: str
    seq: int
    detail: dict[str, Any] = field(default_factory=dict)
    at: float = 0.0


class IngestJobs:
    def __init__(self) -> None:
        self._states: dict[str, JobState] = {}
        self._cond = threading.Condition()

    def update(self, job_id: str, stage: Stage, **detail: Any) -> None:
        with self._cond:
            self._expire()
            previous = self._states.get(job_id)
            if previous is not None and previous.stage in TERMINAL:
                return
            self._states[job_id] = JobState(
                stage=stage,
                label=LABELS[stage],
                seq=(previous.seq + 1) if previous else 0,
                detail=detail,
                at=time.monotonic(),
            )
            self._cond.notify_all()

    def done(self, job_id: str, **detail: Any) -> None:
        self.update(job_id, "done", **detail)

    def fail(self, job_id: str, code: str, message: str) -> None:
        self.update(job_id, "error", code=code, message=message)

    def get(self, job_id: str) -> JobState | None:
        with self._cond:
            return self._states.get(job_id)

    def follow(
        self,
        job_id: str,
        *,
        appear_timeout: float = 30.0,
        idle_timeout: float = 600.0,
        keepalive: float = 5.0,
    ) -> Iterator[JobState | None]:
        """Yield each new state until a terminal one; None is a keep-alive during silence."""
        start = last_change = time.monotonic()
        seen = -1
        while True:
            with self._cond:
                state = self._states.get(job_id)
                if state is None or state.seq == seen:
                    self._cond.wait(timeout=keepalive)
                    state = self._states.get(job_id)
            if state is not None and state.seq != seen:
                seen, last_change = state.seq, time.monotonic()
                yield replace(state)
                if state.stage in TERMINAL:
                    return
                continue
            waited = time.monotonic()
            if (state is None and waited - start > appear_timeout) or (
                state is not None and waited - last_change > idle_timeout
            ):
                return
            yield None

    def _expire(self) -> None:
        now = time.monotonic()
        for key in [k for k, s in self._states.items() if now - s.at > TTL_S]:
            del self._states[key]
        while len(self._states) >= MAX_JOBS:
            del self._states[next(iter(self._states))]


class Progress:
    """Reports stages of one job; a no-op without a job id."""

    def __init__(self, jobs: IngestJobs | None = None, job_id: str | None = None) -> None:
        self.jobs, self.job_id = jobs, job_id

    def __call__(self, stage: Stage, **detail: Any) -> None:
        if self.jobs is not None and self.job_id:
            self.jobs.update(self.job_id, stage, **detail)
