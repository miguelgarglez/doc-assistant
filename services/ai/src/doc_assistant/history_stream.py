"""Record an explicitly enabled stream after its generator has closed."""

from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

from doc_assistant.api import queued_ask_stream
from doc_assistant.ask_capacity import AskCapacity
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
