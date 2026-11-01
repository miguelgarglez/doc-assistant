"""Almacén SQLite: chunks + FTS5 + vec; ingest idempotente."""

from __future__ import annotations

from pathlib import Path

from doc_assistant.chunking import chunk_pdf
from doc_assistant.ingest import ingest_pdfs
from doc_assistant.model_fakes import FakeEmbedder
from doc_assistant.store import ChunkStore


def test_upsert_and_search(
    tmp_path: Path, synthetic_pdf: Path, fake_embedder: FakeEmbedder
) -> None:
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


def test_vector_search_zero_vector_does_not_crash(
    tmp_path: Path, synthetic_pdf: Path, fake_embedder: FakeEmbedder
) -> None:
    """Un vector de norma 0 (p. ej. embedder simulado) da distancia NULL: similitud 0, sin 500."""
    store = ChunkStore(tmp_path / "z.db", dim=fake_embedder.dim)
    chunks = chunk_pdf(synthetic_pdf, doc="manual")
    store.upsert(chunks, [[0.0] * fake_embedder.dim for _ in chunks])
    hits = store.vector_search([0.0] * fake_embedder.dim, k=3)
    assert hits and all(score == 0.0 for _, score in hits)


def test_old_schema_is_moved_aside_not_deleted(tmp_path: Path) -> None:
    """Un índice de otra versión de esquema se renombra a .bak y se recrea vacío."""
    import sqlite3

    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, doc TEXT)")
    con.commit()
    con.close()
    store = ChunkStore(db, dim=8)
    assert (tmp_path / "old.db.schema-v0.bak").exists()
    assert store.count() == 0
    ChunkStore(db, dim=8)  # misma versión: no se aparta otra vez
    assert len(list(tmp_path.glob("*.bak"))) == 1
