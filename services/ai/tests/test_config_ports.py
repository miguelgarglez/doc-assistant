"""Model ports come from DOC_ASSISTANT_*_PORT, with the old values as defaults."""

from pathlib import Path

import pytest

from doc_assistant.config import expand_env, load_config

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config" / "config.yaml"
PORT_VARS = [
    "DOC_ASSISTANT_LLM_PORT",
    "DOC_ASSISTANT_EMBEDDINGS_PORT",
    "DOC_ASSISTANT_RERANKER_PORT",
    "DOC_ASSISTANT_OCR_PORT",
]


@pytest.fixture(autouse=True)
def clean_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in PORT_VARS:
        monkeypatch.delenv(name, raising=False)


def test_repo_config_keeps_the_default_ports_without_variables(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(REPO_CONFIG)
    assert cfg.llm.base_url == "http://127.0.0.1:8081"
    assert cfg.embeddings.base_url == "http://127.0.0.1:8082"
    assert cfg.reranker.base_url == "http://127.0.0.1:8083"
    assert cfg.ocr.base_url == "http://127.0.0.1:8084"


def test_repo_config_follows_the_variables(monkeypatch):
    monkeypatch.setenv("DOC_ASSISTANT_LLM_PORT", "8181")
    monkeypatch.setenv("DOC_ASSISTANT_OCR_PORT", "8184")
    cfg = load_config(REPO_CONFIG)
    assert cfg.llm.url == "http://127.0.0.1:8181/v1/chat/completions"
    assert cfg.ocr.base_url == "http://127.0.0.1:8184"
    assert cfg.embeddings.base_url == "http://127.0.0.1:8082"


def test_a_port_that_is_not_a_number_is_rejected(monkeypatch):
    monkeypatch.setenv("DOC_ASSISTANT_RERANKER_PORT", "abc")
    with pytest.raises(ValueError, match="puerto"):
        load_config(REPO_CONFIG)


def test_ollama_runtime_ignores_the_llama_port_wherever_it_is(monkeypatch):
    assert load_config(REPO_CONFIG).ocr.ollama_url() == "http://127.0.0.1:11434"
    monkeypatch.setenv("DOC_ASSISTANT_OCR_PORT", "8184")
    assert load_config(REPO_CONFIG).ocr.ollama_url() == "http://127.0.0.1:11434"


def test_expand_env_defaults_and_missing_names(monkeypatch):
    monkeypatch.setenv("X_SET", "1")
    assert expand_env({"a": ["${X_SET}", "${X_NOPE:-7}", "plain", 3]}) == {
        "a": ["1", "7", "plain", 3]
    }
    with pytest.raises(ValueError, match="X_NOPE"):
        expand_env("${X_NOPE}")
