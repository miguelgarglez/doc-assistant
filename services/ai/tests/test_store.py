"""Almacén SQLite: chunks + FTS5 + vec; ingest idempotente."""

from __future__ import annotations

from pathlib import Path

from doc_assistant.adapters import FakeEmbedder
from doc_assistant.chunking import chunk_pdf
from doc_assistant.ingest import ingest_pdfs
from doc_assistant.store import ChunkStore


def test_upsert_and_search(tmp_path: Path, synthetic_pdf: Path, fake_embedder: FakeEmbedder) -> None:
    db = tmp_path / "a.db"
    store = ChunkStore(db, dim=fake_embedder.dim)
    chunks = chunk_pdf(synthetic_pdf, doc="manual")
    embs = fake_embedder.embed([c["text"] for c in chunks])
    store.upsert(chunks, embs)
    assert store.count() == len(chunks)

    bm = store.bm25("seguridad voltaje", k=5)
    assert bm
    vec = store.vector_search(fake_embedder.embed(["24 V"])[0], k=5)
    assert vec


def test_ingest_idempotent(
    tmp_path: Path, synthetic_pdf: Path, fake_embedder: FakeEmbedder, config_path: Path
) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    target = pdf_dir / "manual.pdf"
    target.write_bytes(synthetic_pdf.read_bytes())

    r1 = ingest_pdfs(config_path, pdf_dir, embedder=fake_embedder)
    r2 = ingest_pdfs(config_path, pdf_dir, embedder=fake_embedder)

    assert r1["n_chunks"] == r2["n_chunks"]
    assert r1["chunk_ids"] == r2["chunk_ids"]
    assert r1["n_chunks"] > 0

    store = ChunkStore.from_config(config_path)
    assert store.count() == r1["n_chunks"]
