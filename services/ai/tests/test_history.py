import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from doc_assistant.history import HistoryStore


def test_history_is_separate_and_feedback_copies_server_trace(tmp_path):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    trace = {"question": "¿Cuánto?", "citations": [{"quote": "12 €"}]}
    store.record("r1", "c1", "2026-01-01T00:00:00Z", trace)
    store.record("r2", "c2", "2026-01-02T00:00:00Z", {"question": "otra"})
    assert store.get("missing") is None
    assert store.list("c1") == [trace]
    assert not store.add_feedback("f0", "missing", "now", "otro", None)
    assert store.add_feedback("f1", "r1", "now", "incorrecta", "revisar")
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM requests WHERE request_id = 'r1'")
        saved = db.execute("SELECT trace_json FROM feedback WHERE feedback_id = 'f1'").fetchone()
    assert saved is not None
    assert json.loads(saved[0]) == trace


def test_duplicate_request_is_not_overwritten(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("r", "c", "now", {"answer": "original"})
    with pytest.raises(sqlite3.IntegrityError):
        store.record("r", "c", "now", {"answer": "changed"})
    assert store.get("r") == {"answer": "original"}


def test_concurrent_writers_preserve_all_records(tmp_path):
    store = HistoryStore(tmp_path / "history.db")

    def write(i):
        store.record(str(i), "c", f"{i:03d}", {"id": i})

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write, range(20)))
    assert [item["id"] for item in store.list("c", 20)] == list(reversed(range(20)))
