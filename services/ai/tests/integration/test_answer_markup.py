"""Template answers are valid Markdown, their citations match the question, markers sit on elements."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from doubles import FakeEmbedder
from markup import SECTIONS, assert_segments_tile, assert_valid_markdown, make_pdf

from doc_assistant.application.answers.meta import answer_meta, classify
from doc_assistant.bootstrap import ingest_pdfs, save_and_ingest_pdf, source_service
from doc_assistant.config import load_config


@pytest.fixture
def indexed(config_path: Path, tmp_path: Path, invoice_json: Path) -> Path:
    docs = tmp_path / "pdfs"
    docs.mkdir()
    make_pdf(docs / "ACME-200.pdf", "Unidad demo ACME-200 Manual de instalación")
    make_pdf(docs / "ACME-300.pdf", "Unidad demo ACME-300 Guía rápida")
    ingest_pdfs(config_path, docs, invoice_path=invoice_json, embedder=FakeEmbedder())
    return config_path


def meta(config_path: Path, question: str) -> dict[str, Any]:
    cfg = load_config(config_path)
    service = source_service(cfg)
    sources = service.list_sources()
    intent, matched = classify(question, sources)
    assert intent != "rag", question
    return answer_meta(service.meta_chunks(), intent, matched, sources, question)


QUESTIONS = [
    "¿De qué trata ACME-200?",
    "¿Qué documentos tienes?",
    "¿Qué facturas tengo?",
    "¿Qué fuentes hay?",
    "¿Qué sabes hacer?",
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_meta_answers_are_valid_markdown_with_tiling_segments(indexed: Path, question: str) -> None:
    result = meta(indexed, question)
    assert_valid_markdown(result["answer"])
    assert_segments_tile(result)


def test_document_answer_lists_each_section_as_one_cited_bullet(indexed: Path) -> None:
    result = meta(indexed, "¿De qué trata ACME-200?")
    bullets = [s for s in result["segments"] if s["text"].lstrip("\n").startswith("- ")]
    assert len(bullets) == len(SECTIONS)
    assert "- §2.1 Cableado (p. 1)" in result["answer"]
    assert "- §4 Mantenimiento (p. 2)" in result["answer"]
    for segment in bullets:
        assert len(segment["refs"]) == 1
        citation = result["citations"][segment["refs"][0]]
        assert citation["quote"] in citation["fragment"]


def test_inventory_of_invoices_cites_only_invoices(indexed: Path) -> None:
    result = meta(indexed, "¿Qué facturas tengo?")
    assert {c["doc_id"].split("-")[0] for c in result["citations"]} == {"inv"}
    assert len(result["citations"]) == 1
    assert "FAC-2024-001" in result["answer"]
    assert "ACME-200" not in result["answer"].split("También hay")[0]


def test_inventory_of_documents_cites_one_per_document(indexed: Path) -> None:
    result = meta(indexed, "¿Qué documentos tienes?")
    docs = [c["doc_id"] for c in result["citations"]]
    assert len(docs) == len(set(docs)) == 2
    assert all(d.startswith("pdf-") for d in docs)
    assert "FAC-2024-001" not in result["answer"].split("También hay")[0]
    cited_bullets = [s for s in result["segments"] if s["text"].lstrip("\n").startswith("- ")]
    assert [len(s["refs"]) for s in cited_bullets] == [1, 1]


def test_general_inventory_has_one_citation_per_source(indexed: Path) -> None:
    result = meta(indexed, "¿Qué fuentes hay?")
    assert len(result["citations"]) == 3
    assert len({c["doc_id"] for c in result["citations"]}) == 3


def test_names_with_markdown_characters_render_literally(config_path: Path, tmp_path: Path) -> None:
    docs = tmp_path / "pdfs"
    docs.mkdir()
    make_pdf(docs / "my_doc_v2.pdf", "Manual _raro_ de *prueba*")
    ingest_pdfs(config_path, docs, embedder=FakeEmbedder())
    result = meta(config_path, "¿Qué documentos tienes?")
    assert "my\\_doc\\_v2" in result["answer"] and "\\_raro\\_" in result["answer"]
    assert_valid_markdown(result["answer"])


def test_api_returns_segments_and_inline_source(
    indexed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    from doc_assistant.bootstrap import create_app

    with TestClient(create_app(indexed)) as client:
        body = client.post("/ask", json={"question": "¿Qué documentos tienes?"}).json()
    assert body["inline"] == "template" and body["segments"]
    assert "".join(s["text"] for s in body["segments"]) == body["answer"]
    json.dumps(body)


def test_pdf_fixture_is_ingested_with_headings(config_path: Path, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "x.pdf", "Titulo")
    out = save_and_ingest_pdf(config_path, pdf.read_bytes(), "x.pdf", embedder=FakeEmbedder())
    assert out["n_chunks"] == len(SECTIONS)
