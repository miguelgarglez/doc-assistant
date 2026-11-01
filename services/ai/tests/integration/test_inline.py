"""Inline citation segments: model output is validated, rules fill in, nothing is invented."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from doubles import FakeEmbedder, FakeLLM, FakeReranker
from markup import make_pdf

from doc_assistant.bootstrap import ask, ingest_pdfs
from doc_assistant.config import load_config
from doc_assistant.infra.storage.chunks import ChunkStore

ANSWER = "Usar cable de 2.5 mm2 para alimentar. La parada tarda menos de 500 ms."


def raw(*pairs: tuple[str, list[str]]) -> list[dict[str, Any]]:
    return [{"text": t, "chunk_ids": ids} for t, ids in pairs]


@pytest.fixture
def pipeline(config_path: Path, tmp_path: Path) -> tuple[Path, dict[str, str]]:
    docs = tmp_path / "pdfs"
    docs.mkdir()
    make_pdf(docs / "ACME-200.pdf", "Unidad demo ACME-200")
    ingest_pdfs(config_path, docs, embedder=FakeEmbedder())
    store = ChunkStore(load_config(config_path).db, 8)
    try:
        ids = {s: store.get_by_section(s)["chunk_id"] for s in ("2.1", "3")}
    finally:
        store.db.close()
    return config_path, ids


def ask_with(config_path: Path, mode: str, response: dict[str, Any]) -> dict[str, Any]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["inline_citations"] = mode
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return ask(
        config_path,
        "¿Qué cable usar y cuánto tarda la parada?",
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
        llm=FakeLLM(response=response),
    )


def llm_response(ids: dict[str, str], segments: Any = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "answerable": True,
        "answer": ANSWER,
        "citations": [
            {"chunk_id": ids["2.1"], "quote": "cable de 2.5 mm2"},
            {"chunk_id": ids["3"], "quote": "menos de 500 ms"},
        ],
    }
    if segments is not None:
        out["segments"] = segments
    return out


def test_pipeline_model_mode_returns_model_segments(pipeline: tuple[Path, dict[str, str]]) -> None:
    path, ids = pipeline
    segments = raw(
        ("Usar cable de 2.5 mm2 para alimentar.", [ids["2.1"]]),
        ("La parada tarda menos de 500 ms.", [ids["3"]]),
    )
    result = ask_with(path, "model", llm_response(ids, segments))
    assert result["ok"] and result["inline"] == "model"
    assert "".join(s["text"] for s in result["segments"]) == ANSWER
    assert [result["citations"][s["refs"][0]]["chunk_id"] for s in result["segments"]] == [
        ids["2.1"],
        ids["3"],
    ]


def test_pipeline_bad_model_segments_fall_back_to_rules(
    pipeline: tuple[Path, dict[str, str]],
) -> None:
    path, ids = pipeline
    result = ask_with(path, "model", llm_response(ids, raw(("Frase inventada.", ["x"]))))
    assert result["ok"] and result["inline"] == "rules" and result["answer"] == ANSWER


def test_pipeline_off_mode_keeps_citations_after_the_answer(
    pipeline: tuple[Path, dict[str, str]],
) -> None:
    path, ids = pipeline
    result = ask_with(path, "off", llm_response(ids))
    assert result["ok"] and result["segments"] == [] and len(result["citations"]) == 2


def test_inline_markers_never_change_the_verdict(pipeline: tuple[Path, dict[str, str]]) -> None:
    path, ids = pipeline
    fabricated = {**llm_response(ids), "answer": "Usar cable de 9 mm2."}
    for mode in ("model", "rules", "off"):
        result = ask_with(path, mode, fabricated)
        assert result["ok"] is False and result["reason"].startswith("verify:")
