"""Invoice storage (table `facturas`), upload and the /ask entry point for invoices.
Planning, resolution and answering live in invoice_query; the derived query index and
its idempotent migration in invoice_index."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from doc_assistant.adapters import build_adapters, build_ocr
from doc_assistant.application.invoices.query import (
    followup_question,
    is_invoice_question,
    plan_and_run,
)
from doc_assistant.application.invoices.upload import upload
from doc_assistant.application.ports.invoice_writer import InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort
from doc_assistant.config import load_config
from doc_assistant.domain.answers.answer_markup import AnswerBuilder, md_escape
from doc_assistant.domain.documents.ids import invoice_doc_id
from doc_assistant.domain.invoices.blocks import build_blocks, follow_ups
from doc_assistant.domain.invoices.fields import display_value
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
        ocr = build_ocr(cfg)
    if embedder is None or llm is None:
        emb, _, default_llm = build_adapters(cfg, fake=False)
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


def invoice_citation(numero: str, campo: str, valor: Any) -> dict[str, Any]:
    """The citation of one stored field; its text is the value as the answer shows it."""
    fragment = "" if valor is None else display_value(campo, valor)
    return {
        "chunk_id": f"{numero}:{campo}",
        "quote": fragment,
        "doc": numero or "",
        "doc_id": invoice_doc_id(numero or ""),
        "section": campo or "",
        "pages": [1],
        "fragment": fragment,
    }


def render_plan_answer(
    result: dict[str, Any], citations: list[dict[str, Any]]
) -> tuple[
    str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]
]:
    """Markdown for a SQL answer (a headline and one cited bullet per invoice or field), plus
    the same rows as blocks and the follow-up questions they allow."""
    out = AnswerBuilder()
    if result.get("headline"):
        out.paragraph(md_escape(result["headline"]))
    by_field = {c["chunk_id"]: c for c in citations}
    for element in result.get("elements") or []:
        refs = [by_field[f"{c['numero']}:{c['campo']}"] for c in element["citations"]]
        out.bullet(md_escape(element["text"]), refs)
    review = result.get("review") or []
    if review:
        out.paragraph(
            "Nota: facturas pendientes de revisión: " + ", ".join(md_escape(n) for n in review)
        )
    answer, _cites, segments = out.build()

    def cite(numero: str, campo: str, valor: Any) -> int:
        citation = by_field.get(f"{numero}:{campo}")
        if citation is None:
            if campo != "numero" or valor != numero:
                raise ValueError("Block value has no selected evidence")
            citation = invoice_citation(numero, campo, numero)
        if citation["quote"] != display_value(campo, valor):
            raise ValueError("Block value differs from selected evidence")
        return out.cite(citation)

    view = result.get("view")
    blocks = build_blocks(view, cite)
    asks = follow_ups(view, lambda fields, numero: followup_question(fields, numero))
    return answer, list(out.citations), segments, blocks, asks


CLARIFY = {
    "aclaracion",
    "factura_ambigua",
    "parte_ambigua",
    "parte_rol_distinto",
    "factura_no_encontrada",
    "parte_no_encontrada",
    "sin_resultados",
}


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
    if result is None:
        return None
    raw = raws[-1] if raws else None
    citations = [
        invoice_citation(cit.get("numero") or "", cit.get("campo") or "", cit.get("valor"))
        for cit in result.get("citations") or []
    ]
    clarification = result.get("clarification")
    if clarification:
        clarification = {
            **clarification,
            "candidates": [
                {
                    "doc": c["numero"],
                    "doc_id": invoice_doc_id(c["numero"]),
                    **{k: v for k, v in c.items() if k != "numero"},
                }
                for c in clarification["candidates"]
            ],
        }
    if result.get("ok"):
        answer, citations, segments, blocks, asks = render_plan_answer(result, citations)
        return {
            "ok": True,
            "answer": answer,
            "citations": citations,
            "segments": segments,
            "blocks": blocks,
            "follow_ups": asks,
            "inline": "template",
            "reason": result.get("reason") or "sql",
            "suggestions": [],
            "latencies": {},
            "raw": {"plans": raws},
        }
    reason = result.get("reason") or "plan_invalido"
    return {
        "ok": False,
        "answer": (result.get("answer") if reason in CLARIFY and result.get("answer") else None)
        or "No dispongo de esa información en los documentos",
        "citations": [],
        "reason": f"invoice:{reason}",
        "suggestions": [],
        "clarification": clarification,
        "latencies": {},
        "raw": {"plans": raws, "last": raw},
    }
