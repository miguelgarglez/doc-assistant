import json

import pytest

from doc_assistant.feedback_export import main
from doc_assistant.history import HistoryStore


def test_export_command_limits_output_to_reviewed_conversation(tmp_path, capsys):
    path = tmp_path / "history.db"
    store = HistoryStore(path)
    for conversation in ("one", "other"):
        store.record(conversation, conversation, "now", {"question": conversation})
        assert store.add_feedback(conversation, conversation, conversation, "now", "otro", None)
        assert store.set_expected_answer(conversation, conversation, "correcta")
        assert store.set_feedback_status(conversation, conversation, "revisado")
    assert main([str(path), "--conversation-id", "one"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["trace"] == {"question": "one"}


def test_export_command_does_not_create_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(SystemExit) as exc:
        main([str(path), "--conversation-id", "one"])
    assert exc.value.code == 2
    assert not path.exists()
