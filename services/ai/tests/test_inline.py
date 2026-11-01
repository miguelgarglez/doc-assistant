"""Inline citation segments: model output is validated, rules fill in, nothing is invented."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from doubles import FakeEmbedder, FakeLLM, FakeReranker
from markup import make_pdf

from doc_assistant.ask import ask, place_inline_citations
from doc_assistant.config import load_config
from doc_assistant.domain.answers.inline import (
    assign_by_rules,
    overlap,
    split_sentences,
    supports,
    validate_model_segments,
)
from doc_assistant.infra.storage.chunks import ChunkStore
from doc_assistant.ingest import ingest_pdfs

CABLE = "[d · t · 2.1. Cableado] Usar cable de 2.5 mm2 para la alimentación principal."
STOP = "[d · t · 3. Parada] La parada se completa en menos de 500 ms."
CITATIONS = [
    {"chunk_id": "c1", "quote": "cable de 2.5 mm2", "fragment": CABLE},
    {"chunk_id": "c2", "quote": "menos de 500 ms", "fragment": STOP},
]
ANSWER = "Usar cable de 2.5 mm2 para alimentar. La parada tarda menos de 500 ms."


def test_split_sentences_tiles_the_answer() -> None:
    for text in (ANSWER, "Uno.\n\n- dos\n- tres", "sin punto", "4.5 m y 3 m. Fin."):
        assert "".join(split_sentences(text)) == text


def test_overlap_and_support() -> None:
    assert overlap("Usar cable de 2.5 mm2", CABLE) == 1.0
    assert supports("Usar cable de 2.5 mm2 para alimentar.", [CABLE])
    assert not supports("Usar cable de 4 mm2 para alimentar.", [CABLE])
    assert not supports("La batería dura diez años.", [CABLE])


def test_rules_put_each_marker_on_its_own_sentence() -> None:
    citations, segments = assign_by_rules(ANSWER, CITATIONS)
    assert "".join(s["text"] for s in segments) == ANSWER
    assert [citations[s["refs"][0]]["chunk_id"] for s in segments] == ["c1", "c2"]


def test_rules_leave_unsupported_sentences_without_marker() -> None:
    answer = ANSWER + " La garantía dura diez años."
    _, segments = assign_by_rules(answer, CITATIONS)
    assert [bool(s["refs"]) for s in segments] == [True, True, False]


def test_rules_renumber_by_first_use() -> None:
    reversed_answer = "La parada tarda menos de 500 ms. Usar cable de 2.5 mm2 para alimentar."
    citations, segments = assign_by_rules(reversed_answer, CITATIONS)
    assert [c["chunk_id"] for c in citations] == ["c2", "c1"]
    assert [s["refs"] for s in segments] == [[0], [1]]


IDS = ["c1", "c2"]


def raw(*pairs: tuple[str, list[str]]) -> list[dict[str, Any]]:
    return [{"text": t, "chunk_ids": ids} for t, ids in pairs]


def test_citations_no_sentence_uses_are_dropped() -> None:
    extra = {
        "chunk_id": "c3",
        "quote": "filtros",
        "fragment": "[d · t · 4. Mantenimiento] Revisar los filtros cada 6 meses.",
    }
    ordered, segments = assign_by_rules(
        "La parada tarda menos de 500 ms.", [CITATIONS[0], extra, CITATIONS[1]]
    )
    assert [c["chunk_id"] for c in ordered] == ["c2"]
    assert segments == [{"text": "La parada tarda menos de 500 ms.", "refs": [0]}]


def test_when_nothing_is_supported_every_citation_stays_for_the_end_list() -> None:
    ordered, segments = assign_by_rules("Respuesta sin ninguna relación.", CITATIONS)
    assert [c["chunk_id"] for c in ordered] == ["c1", "c2"]
    assert all(segment["refs"] == [] for segment in segments)


def test_model_segments_are_accepted_when_supported() -> None:
    model = raw(
        ("Usar cable de 2.5 mm2 para alimentar.", ["c1"]),
        ("La parada tarda menos de 500 ms.", ["c2"]),
    )
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    _, segments = placed
    assert "".join(s["text"] for s in segments) == ANSWER
    assert [s["refs"] for s in segments] == [[0], [1]]


@pytest.mark.parametrize(
    "model",
    [
        None,
        [],
        "texto",
        [{"text": "No está en la respuesta.", "chunk_ids": ["c1"]}],
        [{"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": ["inventado"]}],
        [{"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": "c1"}],
        [
            {"text": "La parada tarda menos de 500 ms.", "chunk_ids": ["c2"]},
            {"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": ["c1"]},
        ],
    ],
)
def test_malformed_model_segments_are_rejected(model: Any) -> None:
    assert validate_model_segments(ANSWER, model, CITATIONS, IDS) is None


def test_segment_whose_fragment_does_not_support_it_loses_its_marker() -> None:
    model = raw(
        ("Usar cable de 2.5 mm2 para alimentar.", ["c2"]),
        ("La parada tarda menos de 500 ms.", ["c2"]),
    )
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    assert [s["refs"] for s in placed[1]] == [[], [0]]


def test_uncovered_text_stays_in_a_segment_without_marker() -> None:
    model = raw(("La parada tarda menos de 500 ms.", ["c2"]))
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    assert "".join(s["text"] for s in placed[1]) == ANSWER
    assert placed[1][0]["refs"] == []


def test_place_inline_degrades_from_model_to_rules_to_none() -> None:
    good = raw(("Usar cable de 2.5 mm2 para alimentar.", ["c1"]))
    assert place_inline_citations("model", ANSWER, CITATIONS, good)[2] == "model"
    assert place_inline_citations("model", ANSWER, CITATIONS, None)[2] == "rules"
    assert place_inline_citations("rules", ANSWER, CITATIONS, good)[2] == "rules"
    assert place_inline_citations("off", ANSWER, CITATIONS, good) == (CITATIONS, [], "none")
    unrelated = "Nada que ver con los fragmentos de este documento."
    assert place_inline_citations("rules", unrelated, CITATIONS, None) == (CITATIONS, [], "none")


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
