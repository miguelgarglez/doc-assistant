"""Invoice storage (table `facturas`), upload and the /ask entry point for invoices.
Planning, resolution and answering live in invoice_query; the derived query index and
its idempotent migration in invoice_index."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from doc_assistant import bootstrap
from doc_assistant.application.invoices.answers import format_answer
from doc_assistant.application.invoices.query import (
    is_invoice_question,
    plan_and_run,
)
from doc_assistant.application.invoices.upload import upload
from doc_assistant.application.ports.invoice_writer import InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort
from doc_assistant.config import load_config
from doc_assistant.domain.documents.ids import invoice_doc_id
from doc_assistant.infra.invoices.reader import SqliteInvoiceReader
from doc_assistant.infra.invoices.sqlite import InvoiceDB
from doc_assistant.infra.invoices.writer import SqliteInvoiceWriter
from doc_assistant.infra.storage.chunks import ChunkStore


def list_invoices(path: str | Path) -> list[dict[str, Any]]:
    db = InvoiceDB(str(path))
    try:
        return db.rows()
    finally:
        db.con.close()


def upload_invoice(
    config_path: str | Path,
    image: bytes,
    filename: str,
    *,
    ocr: OcrPort | None = None,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Extract, persist SQL row, index chunks+image in the same retrieval store."""
    cfg = load_config(config_path)
    if ocr is None:
        ocr = bootstrap.build_ocr(cfg)
    if embedder is None or llm is None:
        emb, _, default_llm = bootstrap.build_adapters(cfg)
        embedder = embedder or emb
        llm = llm or default_llm

    def writer_factory(model: Embedder) -> InvoiceWriter:
        dim = getattr(model, "dim", None) or cfg.embeddings.dim or 8
        return SqliteInvoiceWriter(cfg.db, cfg.data_dir, dim)

    return upload(
        image,
        filename,
        ocr=ocr,
        llm=llm,
        embedder=embedder,
        writer_factory=writer_factory,
        progress=progress,
    )


def invoice_image(config_path: str | Path, invoice_id: str) -> bytes | None:
    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    try:
        row = db.get(invoice_id)
    finally:
        db.con.close()
    if row is None:
        return None
    store = ChunkStore(cfg.db, dim=cfg.embeddings.dim or 8)
    try:
        png = store.page(invoice_doc_id(row["numero"]), 1)
    finally:
        store.db.close()
    if png is not None:
        return png
    fichero = row.get("fichero") or ""
    if fichero:
        path = cfg.data_dir / fichero
        if path.is_file():
            return path.read_bytes()
    return None


def ask_invoices(
    config_path: str | Path,
    question: str,
    *,
    llm: LLM,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Invoice questions go to the structured path and stay there (no RAG fallback).
    Returns None only when the question is not about invoices."""
    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    try:
        if not is_invoice_question(question, SqliteInvoiceReader(db.con)):
            return None
        result, raws = plan_and_run(SqliteInvoiceReader(db.con), question, llm.chat, trace)
    finally:
        db.con.close()
    return format_answer(result, raws)
