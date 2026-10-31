from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from doc_assistant.adapters import FakeEmbedder
from doc_assistant.api import create_app
from doc_assistant.config import load_config
from doc_assistant.ingest import ingest_pdfs
from doc_assistant.store import ChunkStore


def test_ingest_replaces_old_chunks_and_renders_pages(
    config_path: Path, synthetic_pdf: Path
) -> None:
    first = ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    again = ingest_pdfs(config_path, synthetic_pdf.parent, embedder=FakeEmbedder())
    assert first["chunk_ids"] == again["chunk_ids"]
    cfg = load_config(config_path)
    store = ChunkStore(cfg.db, dim=8)
    assert store.count() == first["n_chunks"]
    assert store.page("manual", 1).startswith(b"\x89PNG")
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
        assert client.get("/sources/manual/pages/1").headers["content-type"] == "image/png"
        assert client.get("/sources/manual/pages/2").status_code == 404
        assert client.get("/health").json() == {"status": "ok"}
        assert (
            client.post("/invoices", json={"numero": "SYN-1", "importe_total": "12"}).status_code
            == 200
        )
        assert client.get("/invoices").json()[0]["numero"] == "SYN-1"


def test_invalid_config_fails_at_startup(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("top_k: 0\n")
    with pytest.raises(ValueError), TestClient(create_app(config)):
        pass
