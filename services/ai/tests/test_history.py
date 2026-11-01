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
    assert store.get("c1", "missing") is None
    assert store.get("c2", "r1") is None
    assert store.list_page("c1")[0] == [trace]
    assert not store.add_feedback("f0", "c1", "missing", "now", "otro", None)
    assert not store.add_feedback("wrong", "c2", "r1", "now", "otro", None)
    assert store.add_feedback("f1", "c1", "r1", "now", "incorrecta", "revisar")
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
    assert store.get("c", "r") == {"answer": "original"}


def test_concurrent_writers_preserve_all_records(tmp_path):
    store = HistoryStore(tmp_path / "history.db")

    def write(i):
        store.record(str(i), "c", f"{i:03d}", {"id": i})

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write, range(20)))
    assert [item["id"] for item in store.list_page("c", limit=20)[0]] == list(reversed(range(20)))


def test_pages_are_stable_when_timestamps_tie_and_new_requests_arrive(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    for request_id in ("a", "b", "c", "d", "e"):
        store.record(request_id, "c", "2026-01-01", {"id": request_id})
    store.record("other", "different", "2026-01-01", {"id": "other"})
    first, cursor = store.list_page("c", limit=2)
    store.record("new", "c", "2026-01-02", {"id": "new"})
    second, cursor = store.list_page("c", limit=2, before=cursor)
    third, cursor = store.list_page("c", limit=2, before=cursor)
    assert [x["id"] for x in first + second + third] == ["e", "d", "c", "b", "a"]
    assert cursor is None
    for invalid_limit in (0, -1, 101):
        with pytest.raises(ValueError):
            store.list_page("c", limit=invalid_limit)
