from decimal import Decimal

from doc_assistant.adapters import FakeLLM, FakeOCR
from doc_assistant.invoice_extract import extract_invoice, parse_es_decimal
from doc_assistant.invoices import InvoiceDB, run_plan


def test_decimal_requires_complete_valid_value():
    assert parse_es_decimal("1.234,56") == Decimal("1234.56")
    assert parse_es_decimal("abc123") is None
    assert parse_es_decimal("1.2.3") is None


def test_unsubstantiated_text_is_null_and_flagged():
    result = extract_invoice(
        b"image",
        ocr=FakeOCR("Factura F-1"),
        llm=FakeLLM({"invoice_number": "F-1", "seller_name": "Inventado"}),
    )
    assert result["record"]["emisor"] is None
    assert result["flags"]["emisor"] == "sin_evidencia"


def test_exact_invoice_precedes_normalized_and_ambiguous_refuses():
    db = InvoiceDB()
    db.upsert({"numero": "F-1", "emisor": "A"})
    db.upsert({"numero": "F/1", "emisor": "B"})
    plan = {"kind": "campos", "campos": ["emisor"]}
    assert "A" in run_plan(db, {**plan, "numero": "F-1"})["answer"]
    assert run_plan(db, {**plan, "numero": "f1"})["reason"] == "factura_ambigua"


def test_sum_refuses_incomplete_coverage_and_text_equality_is_exact():
    db = InvoiceDB()
    db.upsert({"numero": "1", "emisor": "ACME SA", "importe_total": "100"})
    db.upsert({"numero": "2", "emisor": "ACME", "importe_total": "bad"})
    assert not run_plan(db, {"kind": "sumar", "campos": ["importe_total"]})["ok"]
    result = run_plan(
        db, {"kind": "filtro", "filtro_campo": "emisor", "filtro_op": "=", "filtro_valor": "acme"}
    )
    assert result["answer"] == "Facturas: 2"


def test_upload_limits_and_symlink_confinement(config_path, tmp_path, synthetic_pdf):
    import yaml
    from fastapi.testclient import TestClient

    from doc_assistant.api import create_app

    cfg = yaml.safe_load(config_path.read_text())
    cfg["upload_pdf_max_bytes"] = 100
    cfg["upload_image_max_bytes"] = 4
    config_path.write_text(yaml.safe_dump(cfg))
    with TestClient(create_app(config_path)) as client:
        response = client.post("/documents", files={"file": ("a.pdf", synthetic_pdf.read_bytes())})
        assert response.status_code == 413
        assert response.json()["code"] == "upload_too_large"
        response = client.post("/invoices/upload", files={"file": ("a.png", b"\x89PNGx")})
        assert response.status_code == 413
    cfg["upload_pdf_max_bytes"] = 1000000
    config_path.write_text(yaml.safe_dump(cfg))
    (tmp_path / "data" / "documents").symlink_to(tmp_path, target_is_directory=True)
    with TestClient(create_app(config_path)) as client:
        response = client.post("/documents", files={"file": ("a.pdf", synthetic_pdf.read_bytes())})
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_directory"


def test_adapters_reject_invalid_indices_and_dimensions(monkeypatch):
    import pytest

    from doc_assistant.adapters import AdapterError, HttpEmbedder, HttpReranker

    monkeypatch.setattr(
        "doc_assistant.adapters._request_json",
        lambda *a, **k: {"data": [{"index": 0, "embedding": [1.0]}]},
    )
    with pytest.raises(AdapterError):
        HttpEmbedder("url", "model", 1, 2).embed(["a"])
    monkeypatch.setattr(
        "doc_assistant.adapters._request_json",
        lambda *a, **k: {"results": [{"index": 2, "relevance_score": 1}]},
    )
    with pytest.raises(AdapterError):
        HttpReranker("url", "model", 1).rerank("q", ["a"])


def test_failed_invoice_embedding_does_not_write_file_or_row(config_path, tmp_path):
    import pytest

    from doc_assistant.invoices import upload_invoice

    class BrokenEmbedder:
        dim = 8

        def embed(self, texts):
            raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        upload_invoice(
            config_path,
            b"image",
            "a.png",
            ocr=FakeOCR("Factura F-1"),
            llm=FakeLLM({"invoice_number": "F-1"}),
            embedder=BrokenEmbedder(),
        )
    assert not (tmp_path / "data" / "invoices" / "a.png").exists()
    db = InvoiceDB(str(tmp_path / "test.db"))
    assert db.rows() == []
    db.con.close()


def test_pdf_page_limit_and_sync_handlers(config_path, synthetic_pdf):
    import inspect

    import yaml
    from fastapi.testclient import TestClient

    from doc_assistant.api import create_app

    cfg = yaml.safe_load(config_path.read_text())
    cfg["upload_pdf_max_pages"] = 1
    config_path.write_text(yaml.safe_dump(cfg))
    from reportlab.pdfgen.canvas import Canvas

    canvas = Canvas(str(synthetic_pdf))
    canvas.showPage()
    canvas.showPage()
    canvas.save()
    app = create_app(config_path)
    for route in app.routes:
        if getattr(route, "path", "") in ("/documents", "/invoices/upload"):
            assert not inspect.iscoroutinefunction(route.endpoint)
    with TestClient(app) as client:
        response = client.post("/documents", files={"file": ("a.pdf", synthetic_pdf.read_bytes())})
        assert response.status_code == 413
        assert response.json()["code"] == "upload_too_large"
