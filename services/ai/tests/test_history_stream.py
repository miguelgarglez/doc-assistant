"""Check recording across terminal events and client disconnects."""

import sqlite3
from pathlib import Path

import pytest

from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.history import HistoryStore
from doc_assistant.history_stream import recorded_ask_stream


def test_records_finished_stream(config_path, tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    frames = list(recorded_ask_stream(AskCapacity(1, 0), config_path, "", "r", "c", store))
    assert any("event: done" in frame for frame in frames)
    trace = store.get("c", "r")
    assert trace["status"] == "completed"
    assert trace["transport_status"] == "completed"
    assert trace["conversation_id"] == "c"


def test_records_disconnect_and_releases_capacity(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    capacity = AskCapacity(1, 1)
    capacity.running.acquire()
    stream = recorded_ask_stream(capacity, Path("unused"), "question", "r", "c", store)
    assert "Esperando turno" in next(stream)
    stream.close()
    assert store.get("c", "r")["status"] == "interrupted"
    assert capacity.admitted.acquire(blocking=False)
    capacity.admitted.release()
    capacity.running.release()


def test_storage_failure_is_visible(config_path, tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("r", "c", "earlier", {})
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        list(recorded_ask_stream(AskCapacity(1, 0), config_path, "", "r", "c", store))


def test_records_queue_full(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    capacity = AskCapacity(1, 0)
    capacity.admitted.acquire()
    try:
        frames = list(recorded_ask_stream(capacity, Path("unused"), "question", "r", "c", store))
        assert "queue_full" in frames[0]
        assert store.get("c", "r")["transport_error_code"] == "queue_full"
    finally:
        capacity.admitted.release()


def test_close_after_done_records_completion(config_path, tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    stream = recorded_ask_stream(AskCapacity(1, 0), config_path, "", "r", "c", store)
    assert "event: refusal" in next(stream)
    assert "event: done" in next(stream)
    stream.close()
    assert store.get("c", "r")["transport_status"] == "completed"


def test_outbox_failure_does_not_change_done_stream(config_path):
    from doc_assistant.history_stream import outbox_ask_stream

    class BrokenOutbox:
        def submit(self, *args, **kwargs):
            raise OSError("unavailable")

    frames = list(outbox_ask_stream(AskCapacity(1, 0), config_path, "", "r", "c", BrokenOutbox()))
    assert any("event: done" in frame for frame in frames)
    assert not any("event: error" in frame for frame in frames)


def test_enqueue_failure_is_visible_in_outbox_without_changing_done(config_path, monkeypatch):
    from doc_assistant.application.history.outbox import HistoryOutbox
    from doc_assistant.history_stream import outbox_ask_stream

    class Store:
        def record(self, *args):
            raise AssertionError("must not be called")

    outbox = HistoryOutbox(Store())
    try:

        def fail(*args, **kwargs):
            raise OSError("queue unavailable")

        monkeypatch.setattr(outbox, "submit", fail)
        frames = list(outbox_ask_stream(AskCapacity(1, 0), config_path, "", "r", "c", outbox))
        assert any("event: done" in frame for frame in frames)
        assert outbox.status() == {
            "pending": 0,
            "failures": [{"request_id": "r", "error": "OSError"}],
        }
    finally:
        outbox.close()
