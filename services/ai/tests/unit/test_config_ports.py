import pytest

from doc_assistant.config import expand_env


def test_expand_env_defaults_and_missing_names(monkeypatch):
    monkeypatch.setenv("X_SET", "1")
    assert expand_env({"a": ["${X_SET}", "${X_NOPE:-7}", "plain", 3]}) == {
        "a": ["1", "7", "plain", 3]
    }
    with pytest.raises(ValueError, match="X_NOPE"):
        expand_env("${X_NOPE}")
