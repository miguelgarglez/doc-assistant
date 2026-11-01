from pathlib import Path

import pytest
from doubles import FakeEmbedder
from fastapi.testclient import TestClient

from doc_assistant.api import create_app
from doc_assistant.bootstrap import ingest_pdfs
from doc_assistant.config import load_config
from doc_assistant.domain.documents.ids import pdf_doc_id
from doc_assistant.infra.storage.chunks import ChunkStore


def test_upload_error_reasons_and_transient_models(config_path, tmp_path, monkeypatch):
    import yaml
    from reportlab.lib.pdfencrypt import StandardEncryption
    from reportlab.pdfgen.canvas import Canvas

    from doc_assistant.application.ports.models import AdapterBusy, AdapterTimeout

    cfg = yaml.safe_load(config_path.read_text())
    cfg["upload_pdf_max_bytes"] = 100000
    cfg["upload_pdf_max_pages"] = 1
    config_path.write_text(yaml.safe_dump(cfg))
    protected = tmp_path / "protected.pdf"
    canvas = Canvas(str(protected), encrypt=StandardEncryption("secret"))
    canvas.drawString(50, 700, "Synthetic")
    canvas.save()
    long = tmp_path / "long.pdf"
    canvas = Canvas(str(long))
    canvas.showPage()
    canvas.showPage()
    canvas.save()
    with TestClient(create_app(config_path)) as client:

        def upload(name, data):
            return client.post("/documents", files={"file": (name, data)})

        assert upload("x.txt", b"text").json()["reason"] == "unsupported_type"
        assert upload("x.pdf", b"%PDF broken").json()["reason"] == "pdf_unreadable"
        assert upload("x.pdf", protected.read_bytes()).json()["reason"] == "pdf_protected"
        body = upload("x.pdf", long.read_bytes()).json()
        assert (body["reason"], body["limit"]) == ("page_limit", 1)
        body = upload("x.pdf", b"x" * 100001).json()
        assert (body["reason"], body["limit"]) == ("size_limit", 100000)
        plain = _plain_pdf(tmp_path)
        for exc, code in [
            (AdapterBusy("busy"), "model_busy"),
            (AdapterTimeout("timeout"), "model_timeout"),
            (RuntimeError("private"), "internal_error"),
        ]:

            def fail(*args, exc=exc, **kwargs):
                raise exc

            monkeypatch.setattr("doc_assistant.api.save_and_ingest_pdf", fail)
            response = upload("x.pdf", plain)
            assert response.json()["code"] == code
            assert "private" not in response.text


def _plain_pdf(tmp_path):
    from reportlab.pdfgen.canvas import Canvas

    path = tmp_path / "plain.pdf"
    canvas = Canvas(str(path))
    canvas.drawString(50, 700, "Synthetic")
    canvas.save()
    return path.read_bytes()


def test_source_chunks_only_returns_the_requested_document(
    config_path: Path, synthetic_pdf: Path
) -> None:
    ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    with TestClient(create_app(config_path)) as client:
        source = next(item for item in client.get("/sources").json() if item["kind"] == "pdf")
        chunks = client.get(f"/sources/{source['id']}/chunks").json()
        assert len(chunks) == source["n_chunks"]
        assert chunks[0]["text"]
        assert client.get("/sources/pdf-missing/chunks").json() == []


def test_ingest_replaces_old_chunks_and_renders_pages(
    config_path: Path, synthetic_pdf: Path
) -> None:
    first = ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    again = ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    assert first["chunk_ids"] == again["chunk_ids"]
    cfg = load_config(config_path)
    store = ChunkStore(cfg.db, dim=8)
    assert store.count() == first["n_chunks"]
    assert store.page(pdf_doc_id("manual"), 1).startswith(b"\x89PNG")
    from reportlab.pdfgen.canvas import Canvas

    canvas = Canvas(str(synthetic_pdf))
    canvas.drawString(50, 800, "Manual nuevo")
    canvas.drawString(50, 780, "1. Seguridad")
    canvas.drawString(50, 760, "Texto cambiado.")
    canvas.save()
    changed = ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    assert store.count() == changed["n_chunks"]
    assert not set(first["chunk_ids"]) & set(changed["chunk_ids"])
    assert all(store.get(cid) is None for cid in first["chunk_ids"])
    store.db.close()
    with TestClient(create_app(config_path)) as client:
        assert (
            client.get(f"/sources/{pdf_doc_id('manual')}/pages/1").headers["content-type"]
            == "image/png"
        )
        assert client.get(f"/sources/{pdf_doc_id('manual')}/pages/2").status_code == 404
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/invoices", json={"numero": "SYN-1"}).status_code == 405


def test_invalid_config_fails_at_startup(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("top_k: 0\n")
    with pytest.raises(ValueError), TestClient(create_app(config)):
        pass


def test_documents_upload_sanitizes_and_is_idempotent_by_hash(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "doc_assistant.bootstrap.build_adapters",
        lambda cfg: (FakeEmbedder(dim=8), None, None),
    )
    payload = synthetic_pdf.read_bytes()
    with TestClient(create_app(config_path)) as client:
        first = client.post(
            "/documents",
            files={"file": ("../../evil name.pdf", payload, "application/pdf")},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["created"] is True
        assert body["doc_id"] == pdf_doc_id("evil_name")
        assert body["path"] == "documents/evil_name.pdf"
        assert body["n_chunks"] > 0
        second = client.post(
            "/documents",
            files={"file": ("other.pdf", payload, "application/pdf")},
        )
        assert second.status_code == 200
        again = second.json()
        assert again["created"] is False
        assert again["content_hash"] == body["content_hash"]
        assert again["path"] == body["path"]
        assert again["chunk_ids"] == body["chunk_ids"]
        bad = client.post(
            "/documents",
            files={"file": ("nota.txt", b"not a pdf", "text/plain")},
        )
        assert bad.status_code == 400
        assert bad.json()["code"] == "invalid_file"


def test_ingest_confines_paths(
    config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "nested").mkdir()
    (data / "escape").symlink_to(tmp_path, target_is_directory=True)
    calls = []
    monkeypatch.setattr(
        "doc_assistant.api.ingest_pdfs",
        lambda _cfg, path: (
            calls.append(path) or {"n_chunks": 0, "chunk_ids": [], "warnings": [], "timings": {}}
        ),
    )
    with TestClient(create_app(config_path)) as client:
        for path in ("../outside", str(tmp_path), "escape"):
            response = client.post("/ingest", json={"directory": path})
            assert response.status_code == 400
            assert response.json()["code"] == "invalid_directory"
        assert client.post("/ingest", json={"directory": "nested"}).status_code == 200
        assert calls == [data / "nested"]
        assert client.post("/ingest", json={}).status_code == 400
        assert client.post("/ingest", json={"directory": "missing"}).status_code == 404


def _serve_status(status: int):  # type: ignore[no-untyped-def]
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_health_components_reports_each_dependency(config_path: Path, synthetic_pdf: Path) -> None:
    import yaml

    ready = _serve_status(200)
    loading = _serve_status(503)
    raw = yaml.safe_load(config_path.read_text())
    raw["llm"]["base_url"] = f"http://127.0.0.1:{ready.server_port}"
    raw["embeddings"]["base_url"] = f"http://127.0.0.1:{loading.server_port}"
    raw["reranker"]["base_url"] = "http://127.0.0.1:9"  # nothing listens here
    raw["ocr"] = {"runtime": "llama", "base_url": f"http://127.0.0.1:{ready.server_port}"}
    config_path.write_text(yaml.safe_dump(raw))
    ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    try:
        with TestClient(create_app(config_path)) as client:
            response = client.get("/health/components")
    finally:
        ready.shutdown()
        loading.shutdown()
    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()["components"]}
    assert set(by_id) == {"ai", "llm", "embeddings", "reranker", "ocr", "sqlite"}
    assert by_id["llm"]["status"] == "ok" and by_id["llm"]["latency_ms"] > 0
    assert by_id["embeddings"]["status"] == "degraded"
    assert by_id["reranker"]["status"] == "unavailable"
    assert by_id["reranker"]["latency_ms"] is None
    assert by_id["ocr"]["status"] == "ok"
    assert by_id["sqlite"]["status"] == "ok"
    assert by_id["sqlite"]["detail"].endswith("fragmentos")


def test_health_components_never_creates_the_index(config_path: Path) -> None:
    cfg = load_config(config_path)
    assert not cfg.db.exists()
    with TestClient(create_app(config_path)) as client:
        by_id = {c["id"]: c for c in client.get("/health/components").json()["components"]}
    assert by_id["sqlite"]["status"] == "degraded"
    assert not cfg.db.exists()
