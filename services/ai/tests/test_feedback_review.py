import io
import json

import pytest

from doc_assistant.feedback_review import main
from doc_assistant.history import HistoryStore

CONFIRM = ["--confirmed-error", "--confirmed-no-sensitive-data"]


def test_review_is_scoped_and_exportable(tmp_path, monkeypatch):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    store.record("r", "c", "now", {"question": "private"})
    assert store.add_feedback("f", "c", "r", "now", "otro", None)
    monkeypatch.setattr("sys.stdin", io.StringIO("respuesta esperada\n"))
    assert main([str(path), "--conversation-id", "other", "--feedback-id", "f", *CONFIRM]) == 1
    assert store.get_feedback("c", "f")["status"] == "nuevo"
    monkeypatch.setattr("sys.stdin", io.StringIO("respuesta esperada\n"))
    with pytest.raises(SystemExit):
        main([str(path), "--conversation-id", "c", "--feedback-id", "f"])
    assert main([str(path), "--conversation-id", "c", "--feedback-id", "f", *CONFIRM]) == 0
    draft = json.loads(next(store.export_reviewed("c")))
    assert draft["expected_answer"] == "respuesta esperada\n"
    assert draft["trace"] == {"request_id": "r", "conversation_id": "c"}


def test_review_rejects_empty_answer_and_missing_database(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setattr("sys.stdin", io.StringIO("answer"))
    with pytest.raises(SystemExit):
        main([str(path), "--conversation-id", "c", "--feedback-id", "f", *CONFIRM])
    assert not path.exists()
    store = HistoryStore(path)
    store.record("r", "c", "now", {})
    assert store.add_feedback("f", "c", "r", "now", "otro", None)
    monkeypatch.setattr("sys.stdin", io.StringIO("\u00a0\n"))
    with pytest.raises(SystemExit):
        main([str(path), "--conversation-id", "c", "--feedback-id", "f", *CONFIRM])
    assert store.get_feedback("c", "f")["status"] == "nuevo"
