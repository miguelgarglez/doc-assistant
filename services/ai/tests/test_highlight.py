"""Cited text is located on its page as rectangles."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
import pytest
from fastapi.testclient import TestClient
from markup import make_pdf

from doc_assistant.api import create_app
from doc_assistant.infra.pdf.highlight import locate, locate_on_page
from doc_assistant.ingest import ingest_pdfs, save_and_ingest_pdf
from doc_assistant.model_fakes import FakeEmbedder


def tmp_dir_of(pdf: Path) -> Path:
    return pdf.parent / "empty"


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "doc.pdf", "Unidad demo ACME-200 Manual de instalación")


def test_locates_a_quote_with_the_page_fractions(pdf: Path) -> None:
    [rect] = locate(pdf, 1, "Usar cable de 2.5 mm2") or []
    assert 0 < rect.x < 0.3 and 0 < rect.y < 1 and 0 < rect.w < 0.6 and 0 < rect.h < 0.05
    below_heading = locate(pdf, 1, "2.1. Cableado") or []
    assert below_heading and below_heading[0].y < rect.y


def test_is_insensitive_to_whitespace_and_case(pdf: Path) -> None:
    exact = locate(pdf, 1, "Usar cable de 2.5 mm2")
    loose = locate(pdf, 1, "usar  CABLE\nde 2.5   mm2")
    assert exact == loose


def test_returns_none_when_the_text_is_not_on_that_page(pdf: Path) -> None:
    assert locate(pdf, 1, "Revisar los filtros") is None
    assert locate(pdf, 2, "Revisar los filtros cada 6 meses")
    assert locate(pdf, 9, "Usar cable") is None
    assert locate(pdf, 1, "texto que no existe") is None


def test_a_quote_over_two_lines_gives_one_rectangle_per_line(tmp_path: Path) -> None:
    from reportlab.pdfgen.canvas import Canvas

    path = tmp_path / "wrap.pdf"
    canvas = Canvas(str(path))
    canvas.drawString(50, 700, "El conector admite hasta")
    canvas.drawString(50, 680, "dieciséis amperios de corriente.")
    canvas.save()
    rects = locate(path, 1, "admite hasta dieciséis amperios") or []
    assert len(rects) == 2 and rects[0].y < rects[1].y
    document = pdfium.PdfDocument(str(path))
    try:
        assert locate_on_page(document, 1, "admite hasta dieciséis amperios") == rects
    finally:
        document.close()


def test_the_title_prefers_the_top_of_the_page_over_the_footer(tmp_path: Path) -> None:
    from reportlab.pdfgen.canvas import Canvas

    path = tmp_path / "title.pdf"
    canvas = Canvas(str(path))
    canvas.drawString(50, 30, "Manual de la unidad demo")
    canvas.drawString(50, 780, "Manual de la unidad demo")
    canvas.save()
    [rect] = locate(path, 1, "Manual de la unidad demo") or []
    assert rect.y < 0.1


def test_endpoint_reports_each_outcome(config_path: Path, pdf: Path, invoice_json: Path) -> None:
    saved = save_and_ingest_pdf(config_path, pdf.read_bytes(), "doc.pdf", embedder=FakeEmbedder())
    doc = saved["doc_id"]
    with TestClient(create_app(config_path)) as client:
        ok = client.get(f"/sources/{doc}/pages/1/highlight", params={"quote": "Usar cable"}).json()
        assert ok["found"] and ok["reason"] == "ok" and ok["rects"][0]["w"] > 0
        miss = client.get(f"/sources/{doc}/pages/1/highlight", params={"quote": "Nada"}).json()
        assert miss == {"page": 1, "found": False, "reason": "not_found", "rects": []}
        assert (
            client.get("/sources/pdf-x/pages/1/highlight", params={"quote": "a"}).status_code == 404
        )
        assert client.get(f"/sources/{doc}/pages/1/highlight").status_code == 422
        ingest_pdfs(
            config_path, tmp_dir_of(pdf), invoice_path=invoice_json, embedder=FakeEmbedder()
        )
        [invoice] = [s for s in client.get("/sources").json() if s["kind"] == "invoice"]
        assert (
            client.get(
                f"/sources/{invoice['id']}/pages/1/highlight", params={"quote": "Factura"}
            ).json()["reason"]
            == "no_positions"
        )
        (config_path.parent / "data" / "documents" / "doc.pdf").rename(
            config_path.parent / "data" / "doc.moved"
        )
        gone = client.get(f"/sources/{doc}/pages/1/highlight", params={"quote": "Usar"}).json()
        assert gone["reason"] == "no_file"
