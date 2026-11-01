import json
import time
import uuid
from collections.abc import Generator, Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.application.ports.models import AdapterError
from doc_assistant.ask_schemas import (
    AskResponse,
    BlocksEvent,
    CitationsEvent,
    ClarificationEvent,
    DoneEvent,
    ErrorEvent,
    RefusalEvent,
    StepEvent,
    StreamEvent,
    TokenEvent,
)
from doc_assistant.bootstrap import ask_events

ASK_QUEUE_TIMEOUT_S = 60.0


def sse(event: BaseModel) -> str:
    data = event.model_dump(mode="json", exclude={"event"})
    name = event.event  # type: ignore[attr-defined]
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def ask_stream_events(
    config_path: Path,
    question: str,
    request_id: str | None = None,
    *,
    trace: dict[str, Any] | None = None,
) -> Iterator[str]:
    """Translate pipeline events into the SSE contract (see docs/streaming.md)."""
    request_id = request_id or str(uuid.uuid4())
    if trace is not None:
        trace["request_id"] = request_id
        trace["transport_status"] = "interrupted"
    try:
        with closing(ask_events(config_path, question, stream=True, trace=trace)) as events:
            yield from _translate_ask_events(events, request_id, trace=trace)
        if trace is not None:
            trace["transport_status"] = "completed"
    except AdapterError as exc:
        if trace is not None:
            trace["transport_status"] = "error"
            trace["transport_error_code"] = exc.code
        yield sse(ErrorEvent(code=exc.code, message=exc.public_message))
    except Exception:  # noqa: BLE001 - the stream must always end with done or error
        if trace is not None:
            trace["transport_status"] = "error"
            trace["transport_error_code"] = "internal_error"
        yield sse(ErrorEvent(code="internal_error", message="Error interno al responder"))


def _translate_ask_events(
    events: Iterator[tuple[str, dict[str, Any]]],
    request_id: str,
    *,
    trace: dict[str, Any] | None = None,
) -> Iterator[str]:
    emitted = False
    completed = False
    for kind, data in events:
        if kind == "step":
            yield sse(StepEvent.model_validate(data))
        elif kind == "token":
            emitted = True
            yield sse(TokenEvent(text=data["text"]))
        else:
            response = AskResponse.model_validate(data)
            if response.ok:
                yield sse(CitationsEvent(citations=response.citations))
                if response.blocks or response.follow_ups:
                    yield sse(BlocksEvent(blocks=response.blocks, follow_ups=response.follow_ups))
            elif response.clarification:
                yield sse(
                    ClarificationEvent(reason=response.reason, clarification=response.clarification)
                )
            else:
                yield sse(
                    RefusalEvent(
                        answer=response.answer,
                        reason=response.reason,
                        retract=emitted,
                        suggestions=response.suggestions,
                    )
                )
            timings = dict(data.get("latencies") or {})
            timings["total"] = round(sum(timings.values()), 4)
            frame = sse(DoneEvent(**response.model_dump(), timings=timings, request_id=request_id))
            if trace is not None:
                trace["transport_status"] = "completed"
            completed = True
            yield frame
    if not completed:
        raise RuntimeError("pipeline ended without a result")


def queued_ask_stream(
    capacity: AskCapacity,
    config_path: Path,
    question: str,
    request_id: str | None = None,
    *,
    trace: dict[str, Any] | None = None,
) -> Generator[str, None, None]:
    started = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    request_id = request_id or str(uuid.uuid4())
    if trace is not None:
        trace.update(
            {
                "trace_schema_version": 1,
                "request_id": request_id,
                "question": question,
                "steps": [],
                "queue_steps": [],
                "started_at": started_at,
                "status": "interrupted",
            }
        )

    def finish_admission(status: str, code: str | None = None) -> None:
        if trace is not None:
            trace.update(
                {
                    "status": status,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "elapsed_s": round(time.monotonic() - started, 4),
                }
            )
            trace["kind"] = "error"
            trace["transport_status"] = status
            if code is not None:
                trace["error_code"] = code
                trace["transport_error_code"] = code

    def queue_step(step: StepEvent) -> str:
        if trace is not None:
            trace["queue_steps"].append(step.model_dump(mode="json", exclude={"event"}))
        return sse(step)

    if not capacity.admitted.acquire(blocking=False):
        finish_admission("error", "queue_full")
        yield sse(
            ErrorEvent(
                code="queue_full",
                message="Hay demasiadas consultas pendientes. Inténtalo de nuevo en unos segundos.",
            )
        )
        return
    acquired = False
    pipeline_started = False
    try:
        acquired = capacity.running.acquire(blocking=False)
        if not acquired:
            yield queue_step(
                StepEvent(id="route", status="running", label="Esperando turno para responder")
            )
            acquired = capacity.running.acquire(timeout=ASK_QUEUE_TIMEOUT_S)
            if not acquired:
                finish_admission("error", "queue_timeout")
                yield sse(
                    ErrorEvent(
                        code="queue_timeout",
                        message="La espera ha sido demasiado larga. Inténtalo de nuevo.",
                    )
                )
                return
            yield queue_step(
                StepEvent(
                    id="route",
                    status="done",
                    label="Turno disponible",
                    elapsed_s=round(time.monotonic() - started, 4),
                )
            )
        if trace is None:
            yield from ask_stream_events(config_path, question, request_id)
        else:
            trace["queue_wait_s"] = round(time.monotonic() - started, 4)
            pipeline_started = True
            yield from ask_stream_events(config_path, question, request_id, trace=trace)
    finally:
        if trace is not None:
            if "finished_at" not in trace:
                finish_admission("interrupted")
            elif pipeline_started:
                trace["pipeline_elapsed_s"] = trace["elapsed_s"]
                trace["started_at"] = started_at
                trace["finished_at"] = datetime.now(UTC).isoformat()
                trace["elapsed_s"] = round(time.monotonic() - started, 4)
        if acquired:
            capacity.running.release()
        capacity.admitted.release()


STREAM_SCHEMA = TypeAdapter(StreamEvent).json_schema(ref_template="#/components/schemas/{model}")
