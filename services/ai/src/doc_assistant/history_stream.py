"""Record an explicitly enabled stream after its generator has closed."""

import logging
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.application.history.outbox import HistoryOutbox
from doc_assistant.ask_stream import queued_ask_stream
from doc_assistant.history import HistoryStore


def recorded_ask_stream(
    capacity: AskCapacity,
    config_path: Path,
    question: str,
    request_id: str,
    conversation_id: str,
    store: HistoryStore,
) -> Iterator[str]:
    """Persist the final trace on completion or disconnect; propagate storage failures."""
    trace: dict[str, Any] = {"conversation_id": conversation_id}
    stream = queued_ask_stream(capacity, config_path, question, request_id, trace=trace)
    try:
        with closing(stream):
            yield from stream
    finally:
        if "started_at" in trace:
            store.record(request_id, conversation_id, trace["started_at"], trace)


def outbox_ask_stream(
    capacity: AskCapacity,
    config_path: Path,
    question: str,
    request_id: str,
    conversation_id: str,
    outbox: HistoryOutbox,
    *,
    ticket: tuple[int, int] | None = None,
) -> Iterator[str]:
    """Enqueue a trace after the stream closes, without exposing storage errors."""
    trace: dict[str, Any] = {"conversation_id": conversation_id}
    stream = queued_ask_stream(capacity, config_path, question, request_id, trace=trace)
    try:
        with closing(stream):
            yield from stream
    finally:
        if "started_at" in trace:
            try:
                outbox.submit(
                    request_id, conversation_id, trace["started_at"], trace, ticket=ticket
                )
            except Exception as exc:  # noqa: BLE001 - storage must not interrupt the stream
                try:
                    outbox.report_failure(request_id, exc)
                except Exception:  # noqa: BLE001 - diagnostics must not interrupt the stream
                    logging.getLogger(__name__).error(
                        "Could not queue history for request_id=%s", request_id
                    )
