from decimal import Decimal

from doc_assistant.infra.invoices.sqlite import InvoiceDB
from doc_assistant.invoice_extract import extract_invoice, parse_es_decimal
from doc_assistant.invoice_query import run_plan
from doc_assistant.model_fakes import FakeLLM, FakeOCR


def test_model_overload_and_timeout_are_preserved_at_transport_boundary(monkeypatch):
    import pytest
    import requests

    from doc_assistant.application.ports.models import AdapterBusy, AdapterTimeout
    from doc_assistant.infra.models.http import _request_json

    for status in (429, 503):
        response = requests.Response()
        response.status_code = status
        monkeypatch.setattr("requests.request", lambda *a, result=response, **k: result)
        with pytest.raises(AdapterBusy) as caught:
            _request_json("POST", "http://model", timeout=1)
        assert caught.value.code == "model_busy"
        assert "http://" not in caught.value.public_message

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("requests.request", timeout)
    with pytest.raises(AdapterTimeout) as caught:
        _request_json("POST", "http://model", timeout=1)
    assert caught.value.code == "model_timeout"


def test_invoice_planner_propagates_model_overload():
    import pytest

    from doc_assistant.application.ports.models import AdapterBusy, AdapterTimeout
    from doc_assistant.invoice_query import plan_and_run

    for error in (AdapterBusy("busy"), AdapterTimeout("timeout")):

        def fail(*args, error=error):
            raise error

        with pytest.raises(type(error)):
            plan_and_run(InvoiceDB().con, "facturas", fail)


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
    plan = {"intent": "valor", "campos": ["emisor"]}
    assert "A" in run_plan(db.con, {**plan, "numero": "F-1"})["answer"]
    assert run_plan(db.con, {**plan, "numero": "f1"})["reason"] == "factura_ambigua"


def test_sum_refuses_incomplete_coverage_and_full_name_beats_partial():
    db = InvoiceDB()
    db.upsert({"numero": "1", "emisor": "ACME Logística SA", "importe_total": "100"})
    db.upsert({"numero": "2", "emisor": "ACME", "importe_total": "bad"})
    assert not run_plan(db.con, {"intent": "sumar", "campos": ["importe_total"]})["ok"]
    result = run_plan(db.con, {"intent": "lista", "parte": "acme"})
    assert result["answer"].startswith("Facturas de ACME: 2")


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

    from doc_assistant.application.ports.models import AdapterError
    from doc_assistant.infra.models.http import HttpEmbedder, HttpReranker

    monkeypatch.setattr(
        "doc_assistant.infra.models.http._request_json",
        lambda *a, **k: {"data": [{"index": 0, "embedding": [1.0]}]},
    )
    with pytest.raises(AdapterError):
        HttpEmbedder("url", "model", 1, 2).embed(["a"])
    monkeypatch.setattr(
        "doc_assistant.infra.models.http._request_json",
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


def test_adapter_cardinality_and_duplicate_indices(monkeypatch):
    import pytest

    from doc_assistant.application.ports.models import AdapterError
    from doc_assistant.infra.models.http import HttpEmbedder, HttpReranker

    for rows in ([{"index": 0, "embedding": [1]}], [{"index": 0, "embedding": [1]}] * 2):
        monkeypatch.setattr(
            "doc_assistant.infra.models.http._request_json",
            lambda *a, rows=rows, **k: {"data": rows},
        )
        with pytest.raises(AdapterError):
            HttpEmbedder("url", "m", 1, 1).embed(["a", "b"])
    for rows in ([{"index": 0, "relevance_score": 1}], [{"index": 0, "relevance_score": 1}] * 2):
        monkeypatch.setattr(
            "doc_assistant.infra.models.http._request_json",
            lambda *a, rows=rows, **k: {"results": rows},
        )
        with pytest.raises(AdapterError):
            HttpReranker("url", "m", 1).rerank("q", ["a", "b"])


def test_review_status_is_exposed_and_warns(config_path):
    from fastapi.testclient import TestClient

    from doc_assistant.api import create_app
    from doc_assistant.config import load_config
    from doc_assistant.infra.invoices.sqlite import InvoiceDB
    from doc_assistant.invoice_query import run_plan

    db = InvoiceDB(str(load_config(config_path).db))
    db.upsert({"numero": "A/120", "importe_total": "10"}, cuadra="0", motivo="suma_no_cuadra")
    for intent in ("valor", "lista", "contar", "sumar"):
        result = run_plan(
            db.con, {"intent": intent, "numero": "A/120", "campos": ["importe_total"]}
        )
        assert "revisión" in result["answer"] and "A/120" in result["answer"]
    db.con.close()
    with TestClient(create_app(config_path)) as client:
        row = client.get("/invoices").json()[0]
        assert (row["estado"], row["motivo"]) == ("revisar", "suma_no_cuadra")


def test_invoice_transaction_rolls_back_and_separates_pdf(config_path, synthetic_pdf, monkeypatch):
    import pytest
    from fastapi.testclient import TestClient

    from doc_assistant.api import create_app
    from doc_assistant.chunking import invoice_doc_id, pdf_doc_id
    from doc_assistant.config import load_config
    from doc_assistant.infra.invoices.sqlite import InvoiceDB
    from doc_assistant.infra.storage.chunks import ChunkStore
    from doc_assistant.ingest import ingest_pdfs
    from doc_assistant.invoices import upload_invoice
    from doc_assistant.model_fakes import FakeEmbedder

    pdf = synthetic_pdf.with_name("A120.pdf")
    pdf.write_bytes(synthetic_pdf.read_bytes())
    ingest_pdfs(config_path, pdf, embedder=FakeEmbedder())
    record = {"numero": "A/120", "importe_total": "10"}
    monkeypatch.setattr(
        "doc_assistant.invoices.extract_invoice",
        lambda *a, **k: {
            "record": record,
            "estado": "revisar",
            "motivo": "suma_no_cuadra",
            "evidencias": {},
            "flags": {},
        },
    )

    class Dummy:
        pass

    upload_invoice(
        config_path, b"first", "a.png", ocr=Dummy(), llm=Dummy(), embedder=FakeEmbedder()
    )
    record["numero"] = "A120"
    upload_invoice(
        config_path, b"other", "b.png", ocr=Dummy(), llm=Dummy(), embedder=FakeEmbedder()
    )
    record["numero"] = "A/120"
    cfg = load_config(config_path)
    with TestClient(create_app(config_path)) as client:
        assert client.get(f"/sources/{invoice_doc_id('A120')}/pages/1").content == b"other"
        assert client.get("/invoices/A%2F120/image").content == b"first"
        assert client.get("/sources/A%2F120/pages/1").content == b"first"
        assert client.get("/sources/A120/pages/1").status_code == 404
        assert client.get(f"/sources/{invoice_doc_id('A/120')}/pages/1").content == b"first"
        assert client.get(f"/sources/{pdf_doc_id('A120')}/pages/1").content.startswith(b"\x89PNG")
    original = ChunkStore.upsert

    def fail(self, chunks, embeddings, *, commit=True):
        original(self, chunks, embeddings, commit=False)
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(ChunkStore, "upsert", fail)
    record["importe_total"] = "20"
    with pytest.raises(RuntimeError):
        upload_invoice(
            config_path, b"second", "a.png", ocr=Dummy(), llm=Dummy(), embedder=FakeEmbedder()
        )
    db = InvoiceDB(str(cfg.db))
    assert db.get("A/120")["importe_total"] == "10"
    db.con.close()
    store = ChunkStore(cfg.db, 8)
    assert store.page(invoice_doc_id("A/120"), 1) == b"first"
    store.db.close()
