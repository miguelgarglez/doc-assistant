"""Invoice storage (table `facturas`), upload and the /ask entry point for invoices.
Planning, resolution and answering live in invoice_query; the derived query index and
its idempotent migration in invoice_index."""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from doc_assistant.adapters import build_adapters, build_ocr
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort
from doc_assistant.chunking import chunk_invoice, invoice_doc_id
from doc_assistant.config import load_config
from doc_assistant.domain.answers.answer_markup import AnswerBuilder, md_escape
from doc_assistant.infra.storage.chunks import SCHEMA_VERSION, ChunkStore, ensure_schema
from doc_assistant.invoice_blocks import build_blocks, follow_ups
from doc_assistant.invoice_extract import extract_invoice
from doc_assistant.invoice_fields import display_value
from doc_assistant.invoice_index import norm_key, sync_derived
from doc_assistant.invoice_query import (
    FIELDS,
    followup_question,
    is_invoice_question,
    plan_and_run,
)


class InvoiceDB:
    def __init__(self, path: str = ":memory:") -> None:
        ensure_schema(path)
        self.con = sqlite3.connect(path)
        cols = ", ".join(f"{k} TEXT" for k in FIELDS)
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
        )
        self.con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.sync()

    def sync(self) -> dict[str, int]:
        """Idempotent migration of the derived query tables (see invoice_index)."""
        return sync_derived(self.con, list(FIELDS))

    def upsert(
        self,
        rec: dict[str, Any],
        fichero: str = "",
        cuadra: str = "",
        motivo: str | None = None,
        *,
        commit: bool = True,
    ) -> None:
        vals = [None if rec.get(k) in (None, "") else str(rec[k]) for k in FIELDS]
        q = ",".join("?" * (len(FIELDS) + 3))
        self.con.execute(
            f"INSERT OR REPLACE INTO facturas VALUES ({q})", [*vals, fichero, cuadra, motivo]
        )
        if commit:
            self.con.commit()
            self.sync()

    def rows(self) -> list[dict[str, Any]]:
        cur = self.con.execute("SELECT * FROM facturas ORDER BY numero")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def get(self, numero: str) -> dict[str, Any] | None:
        want = norm_key(numero)
        rows = self.rows()
        exact = [row for row in rows if row["numero"] == numero]
        hits = exact or [row for row in rows if want and norm_key(row["numero"]) == want]
        return hits[0] if len(hits) == 1 else None


def list_invoices(path: str | Path) -> list[dict[str, Any]]:
    db = InvoiceDB(str(path))
    try:
        return db.rows()
    finally:
        db.con.close()


def sanitize_image_filename(name: str, numero: str) -> str:
    base = Path(name or f"{numero}.png").name
    safe = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._") or numero
    lower = safe.lower()
    if not lower.endswith((".png", ".jpg", ".jpeg")):
        safe = f"{safe}.png"
    return safe


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

    extracted = extract_invoice(image, ocr=ocr, llm=llm, on_stage=progress)
    record = extracted["record"]
    numero = record.get("numero")
    if not numero:
        return {
            "record": record,
            "estado": "revisar",
            "motivo": "sin_numero",
            "evidencias": extracted["evidencias"],
            "flags": extracted["flags"],
        }

    if progress:
        progress("indexing")
    chunks = chunk_invoice(record)
    embeddings = embedder.embed([c["text"] for c in chunks]) if chunks else []

    invoices_dir = cfg.data_dir / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    path = invoices_dir / (
        invoice_doc_id(numero) + Path(sanitize_image_filename(filename, numero)).suffix
    )
    relative = str(path.relative_to(cfg.data_dir))
    fd, temporary = tempfile.mkstemp(dir=invoices_dir, prefix=".invoice-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image)
        dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
        store = ChunkStore(cfg.db, dim=dim)
        try:
            cols = ", ".join(f"{k} TEXT" for k in FIELDS)
            store.db.execute(
                f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
            )
            values = [None if record.get(k) in (None, "") else str(record[k]) for k in FIELDS]
            placeholders = ",".join("?" * (len(FIELDS) + 3))
            store.db.execute(
                f"INSERT OR REPLACE INTO facturas VALUES ({placeholders})",
                [
                    *values,
                    relative,
                    "1" if extracted["estado"] == "ok" else "0",
                    extracted["motivo"],
                ],
            )
            store.replace_document(
                invoice_doc_id(numero), chunks, embeddings, [image], commit=False
            )
            store.db.commit()
        except Exception:
            store.db.rollback()
            raise
        finally:
            store.db.close()
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return {
        "record": record,
        "estado": extracted["estado"],
        "motivo": extracted["motivo"],
        "evidencias": extracted["evidencias"],
        "flags": extracted["flags"],
        "fichero": relative,
    }


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
        if not is_invoice_question(question, db.con):
            return None
        result, raws = plan_and_run(db.con, question, llm.chat, trace)
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
