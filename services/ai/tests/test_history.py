import json
import os
import sqlite3
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from doc_assistant.history import HistoryStore


def test_purge_removes_expired_requests_and_feedback_independently(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("old", "c", "2026-01-01T00:00:00Z", {"question": "old"})
    store.record("new", "c", "2026-02-01T00:00:00Z", {"question": "new"})
    assert store.add_feedback("old-f", "c", "new", "2026-01-01T00:00:00Z", "otro", None)
    assert store.add_feedback("new-f", "c", "old", "2026-02-01T00:00:00Z", "otro", None)

    assert store.purge_before("2026-02-01T00:00:00Z") == (1, 1)
    assert store.get("c", "old") is None
    assert store.get("c", "new") == {"question": "new"}
    assert store.get_feedback("c", "old-f") is None
    assert store.get_feedback("c", "new-f") is not None
    assert store.purge_before("2026-02-01T00:00:00Z") == (0, 0)


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
        saved = db.execute(
            "SELECT trace_json, conversation_id FROM feedback WHERE feedback_id = 'f1'"
        ).fetchone()
    assert saved is not None
    assert json.loads(saved[0]) == trace
    assert saved[1] == "c1"
    assert store.get_feedback("c2", "f1") is None
    assert store.get_feedback("c1", "missing") is None
    assert store.get_feedback("c1", "f1") == {
        "feedback_id": "f1",
        "request_id": "r1",
        "created_at": "now",
        "kind": "incorrecta",
        "comment": "revisar",
        "trace": trace,
        "status": "nuevo",
        "expected_answer": None,
    }


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


def test_existing_feedback_gains_conversation_without_losing_orphans(tmp_path):
    path = tmp_path / "history.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE requests (request_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                created_at TEXT NOT NULL, trace_json TEXT NOT NULL);
            CREATE TABLE feedback (feedback_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                created_at TEXT NOT NULL, kind TEXT NOT NULL, comment TEXT, trace_json TEXT NOT NULL);
            INSERT INTO requests VALUES ('r', 'c', 'now', '{}');
            INSERT INTO feedback VALUES ('f', 'r', 'now', 'otro', NULL, '{}');
            INSERT INTO feedback VALUES ('orphan', 'deleted', 'now', 'otro', NULL, '{}');
        """)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: HistoryStore(path), range(4)))
    HistoryStore(path)
    with sqlite3.connect(path) as db:
        rows = dict(db.execute("SELECT feedback_id, conversation_id FROM feedback"))
    assert rows == {"f": "c", "orphan": None}
    assert HistoryStore(path).get_feedback("c", "f")["status"] == "nuevo"
    assert HistoryStore(path).get_feedback("c", "f")["expected_answer"] is None


def test_wal_initialization_retries_when_database_is_locked(tmp_path, monkeypatch):
    real_connect = sqlite3.connect
    attempts = []

    class BusyOnce(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql == "PRAGMA journal_mode=WAL" and not attempts:
                attempts.append(sql)
                error = sqlite3.OperationalError("database is locked")
                error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                raise error
            return super().execute(sql, parameters)

    monkeypatch.setattr(
        sqlite3, "connect", lambda *args, **kwargs: real_connect(*args, **kwargs, factory=BusyOnce)
    )
    store = HistoryStore(tmp_path / "history.db")
    store.record("r", "c", "now", {"answer": "ok"})
    assert store.get("c", "r") == {"answer": "ok"}
    assert len(attempts) == 1


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_new_history_file_is_private_even_with_permissive_umask(tmp_path):
    path = tmp_path / "history.db"
    old_umask = os.umask(0)
    try:
        store = HistoryStore(path)
        store.record("r", "c", "now", {"question": "private"})
    finally:
        os.umask(old_umask)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert store.get("c", "r") == {"question": "private"}


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_existing_history_file_permissions_are_not_changed(tmp_path):
    path = tmp_path / "history.db"
    path.touch(mode=0o640)
    path.chmod(0o640)
    HistoryStore(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_feedback_pages_survive_request_removal_and_isolate_conversations(tmp_path):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    store.record("r", "c", "now", {"question": "private"})
    store.record("other", "different", "now", {"question": "other"})
    for feedback_id in ("a", "b", "c"):
        assert store.add_feedback(feedback_id, "c", "r", "2026-01-01", "otro", None)
    assert store.add_feedback("other", "different", "other", "2026-01-01", "otro", None)
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM requests WHERE request_id = 'r'")
    first, cursor = store.list_feedback_page("c", limit=2)
    store.record("new", "c", "now", {})
    assert store.add_feedback("new", "c", "new", "2026-01-02", "otro", None)
    second, cursor = store.list_feedback_page("c", limit=2, before=cursor)
    assert [item["feedback_id"] for item in first + second] == ["c", "b", "a"]
    assert all(item["trace"] == {"question": "private"} for item in first + second)
    assert cursor is None
    assert [item["feedback_id"] for item in store.list_feedback_page("different")[0]] == ["other"]
    for invalid_limit in (0, -1, 101):
        with pytest.raises(ValueError):
            store.list_feedback_page("c", limit=invalid_limit)


def test_history_rejects_trace_for_a_different_request(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="request_id"):
        store.record("r1", "c", "now", {"request_id": "r2", "question": "private"})
    assert store.get("c", "r1") is None
    assert not store.add_feedback("f", "c", "r1", "now", "otro", None)
    store.record("r1", "c", "now", {"request_id": "r1"})
    assert store.get("c", "r1") == {"request_id": "r1"}


def test_feedback_review_status_is_scoped_and_survives_reopening(tmp_path):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    store.record("r", "c", "now", {"question": "private"})
    assert store.add_feedback("f", "c", "r", "now", "otro", None)
    assert not store.set_feedback_status("other", "f", "revisado")
    with pytest.raises(ValueError, match="status"):
        store.set_feedback_status("c", "f", "unknown")
    assert store.set_feedback_status("c", "f", "revisado")
    reopened = HistoryStore(path)
    assert reopened.get_feedback("c", "f")["status"] == "revisado"
    assert reopened.list_feedback_page("c")[0][0]["status"] == "revisado"
    assert not reopened.set_feedback_status("c", "missing", "descartado")


def test_expected_answer_is_scoped_and_preserves_snapshot(tmp_path):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    trace = {"question": "¿Cuánto?", "answer": "12 €"}
    store.record("r", "c", "now", trace)
    assert store.add_feedback("f", "c", "r", "now", "incorrecta", None)
    assert not store.set_expected_answer("other", "f", "secret")
    assert store.get_feedback("c", "f")["expected_answer"] is None
    assert store.set_expected_answer("c", "f", "15 €")
    saved = HistoryStore(path).get_feedback("c", "f")
    assert saved["expected_answer"] == "15 €"
    assert saved["trace"] == trace
    assert store.set_expected_answer("c", "f", None)
    assert store.get_feedback("c", "f")["expected_answer"] is None


def test_export_contains_only_reviewed_drafts_with_expected_answers(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    for conversation in ("c", "other"):
        store.record(conversation, conversation, "now", {"question": conversation})
        for feedback_id in (
            f"{conversation}-ready",
            f"{conversation}-empty",
            f"{conversation}-new",
        ):
            assert store.add_feedback(feedback_id, conversation, conversation, "now", "otro", None)
        assert store.set_expected_answer(conversation, f"{conversation}-ready", "15 €")
        assert store.set_feedback_status(conversation, f"{conversation}-ready", "revisado")
        assert store.set_expected_answer(conversation, f"{conversation}-empty", "  ")
        assert store.set_feedback_status(conversation, f"{conversation}-empty", "revisado")
        assert store.set_expected_answer(conversation, f"{conversation}-new", "pending review")

    lines = list(store.export_reviewed("c"))
    assert len(lines) == 1
    assert lines[0].endswith("\n")
    item = json.loads(lines[0])
    assert item["feedback_id"] == "c-ready"
    assert item["expected_answer"] == "15 €"
    assert item["trace"] == {"question": "c"}


def test_history_rejects_trace_for_a_different_conversation(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="conversation_id"):
        store.record("r", "c1", "now", {"conversation_id": "c2"})
    assert store.get("c1", "r") is None
    store.record("r", "c1", "now", {"conversation_id": "c1"})
    assert store.get("c1", "r") == {"conversation_id": "c1"}


def test_feedback_rejects_unknown_kind_without_writing(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("r", "c", "now", {"question": "private"})
    with pytest.raises(ValueError, match="kind"):
        store.add_feedback("f", "c", "r", "now", "unknown", None)
    assert store.get_feedback("c", "f") is None
    for kind in ("incorrecta", "cita_equivocada", "falta_informacion", "otro"):
        assert store.add_feedback(kind, "c", "r", "now", kind, None)


def test_editing_a_reviewed_answer_requires_review_again(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("r", "c", "now", {"question": "question"})
    assert store.add_feedback("f", "c", "r", "now", "otro", None)
    assert store.review_feedback("c", "f", "original")
    assert len(list(store.export_reviewed("c"))) == 1
    assert store.set_expected_answer("c", "f", "original")
    assert store.get_feedback("c", "f")["status"] == "revisado"
    assert store.set_expected_answer("c", "f", "changed")
    assert store.get_feedback("c", "f")["status"] == "nuevo"
    assert list(store.export_reviewed("c")) == []
    assert store.review_feedback("c", "f", "changed")
    assert json.loads(next(store.export_reviewed("c")))["expected_answer"] == "changed"


def test_private_feedback_requires_explicit_context(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    trace = {"question": "Factura de 123 €", "result": {"citations": [{"quote": "123 €"}]}}
    store.record("r", "c", "2026-01-01", trace)
    assert store.add_private_feedback("private", "c", "r", "now", "incorrecta")
    assert store.get_feedback("c", "private")["trace"] == {
        "request_id": "r",
        "conversation_id": "c",
    }
    assert store.add_private_feedback("included", "c", "r", "now", None, include_context=True)
    assert store.get_feedback("c", "included")["trace"] == trace
    assert not store.add_private_feedback("missing", "other", "r", "now", None)


def test_conversation_pages_search_and_delete(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.record("r1", "c1", "2026-01-01", {"question": "alfa"})
    store.record("r2", "c2", "2026-01-02", {"question": "beta"})
    store.record("r3", "c2", "2026-01-03", {"question": "gamma"})
    assert [x["conversation_id"] for x in store.conversations_page(limit=1)] == ["c2"]
    assert [x["conversation_id"] for x in store.conversations_page(limit=1, offset=1)] == ["c1"]
    assert store.conversations_page(search="beta")[0]["count"] == 2
    assert store.add_private_feedback("f", "c2", "r2", "now", None)
    assert store.delete_conversation("c2") == 2
    assert store.get_feedback("c2", "f") is None
    assert store.delete_all() == 1
    assert store.conversations_page() == []


def test_global_review_queue_and_export_only_reviewed(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    for i in range(3):
        store.record(f"r{i}", f"c{i}", f"2026-01-0{i + 1}", {"question": str(i)})
        assert store.add_private_feedback(f"f{i}", f"c{i}", f"r{i}", f"2026-01-0{i + 1}", None)
    assert store.review_feedback("c1", "f1", "correct answer")
    assert [item["feedback_id"] for item in store.feedback_by_status("nuevo", limit=1)] == ["f2"]
    assert [
        item["feedback_id"] for item in store.feedback_by_status("nuevo", limit=1, offset=1)
    ] == ["f0"]
    exported = [json.loads(line) for line in store.export_all_reviewed()]
    assert [(item["feedback_id"], item["conversation_id"]) for item in exported] == [("f1", "c1")]
