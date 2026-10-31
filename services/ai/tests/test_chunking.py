"""Troceado de PDF sintético y factura → chunks citables."""

from __future__ import annotations

import json
from pathlib import Path

from doc_assistant.chunking import chunk_invoice, chunk_pdf, extract_pdf_text


def test_extract_pdf_text_has_sections(synthetic_pdf: Path) -> None:
    pages = extract_pdf_text(synthetic_pdf)
    assert len(pages) >= 1
    joined = "\n".join(p["text"] for p in pages)
    assert "1. Seguridad" in joined
    assert "2.1. Cableado" in joined


def test_chunk_pdf_sections_and_ids(synthetic_pdf: Path) -> None:
    chunks = chunk_pdf(synthetic_pdf, doc="manual")
    assert len(chunks) >= 3
    sections = {c["section"] for c in chunks}
    assert "1" in sections
    assert "2" in sections
    assert "2.1" in sections

    for c in chunks:
        assert c["chunk_id"]
        assert len(c["chunk_id"]) == 12
        assert c["doc"] == "manual"
        assert c["body"]
        assert c["text"].startswith("[manual ·")
        assert " · " in c["text"]

    seg = next(c for c in chunks if c["section"] == "1")
    assert "24 V" in seg["body"]
    assert seg["heading"].startswith("1.")


def test_chunk_pdf_skips_footer(synthetic_pdf: Path) -> None:
    chunks = chunk_pdf(synthetic_pdf, doc="manual")
    for c in chunks:
        assert "ACME Robotics" not in c["body"]


def test_chunk_invoice_fields_and_lines(invoice_json: Path) -> None:
    data = json.loads(invoice_json.read_text(encoding="utf-8"))
    chunks = chunk_invoice(data)
    assert chunks
    docs = {c["doc"] for c in chunks}
    assert docs == {"FAC-2024-001"}

    by_section = {c["section"]: c for c in chunks}
    assert "fecha" in by_section
    assert by_section["fecha"]["body"] == "fecha: 2024-03-15"
    assert "cliente" in by_section
    assert "total" in by_section

    line_chunks = [c for c in chunks if c["section"].startswith("linea_")]
    assert len(line_chunks) == 2
    assert any("Motor brushless" in c["body"] for c in line_chunks)

    for c in chunks:
        assert len(c["chunk_id"]) == 12
        assert c["text"].startswith("[FAC-2024-001 ·")
