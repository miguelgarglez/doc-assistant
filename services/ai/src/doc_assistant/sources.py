"""Catalogue of indexed sources, built only from what the index really holds."""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doc_assistant.chunking import invoice_doc_id, pdf_doc_id
from doc_assistant.config import AppConfig
from doc_assistant.store import ChunkStore


def _section_key(section: str) -> tuple[Any, ...]:
    parts = section.split(".")
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)


def _mtime(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")


def _invoice_rows(db: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facturas'"
    ).fetchone()
    if not exists:
        return {}
    cur = db.execute("SELECT numero, fichero, cuadra, motivo FROM facturas")
    return {r[0]: {"fichero": r[1], "cuadra": r[2], "motivo": r[3]} for r in cur.fetchall()}


def list_sources(cfg: AppConfig) -> list[dict[str, Any]]:
    store = ChunkStore(cfg.db, cfg.embeddings.dim or 8)
    try:
        db = store.db
        chunks: dict[str, list[dict[str, Any]]] = {}
        for row in db.execute(
            "SELECT doc, display_doc, section, heading, title, pages FROM chunks"
        ):
            chunks.setdefault(row["doc"], []).append(dict(row))
        pages = {
            r[0]: r[1] for r in db.execute("SELECT doc, COUNT(*) FROM source_pages GROUP BY doc")
        }
        invoices = _invoice_rows(db)
    finally:
        store.db.close()

    out: list[dict[str, Any]] = []
    for doc in sorted(set(chunks) | set(pages)):
        rows = chunks.get(doc, [])
        is_invoice = doc.startswith("inv-")
        name = rows[0]["display_doc"] if rows else doc.split("-", 1)[-1]
        sections = sorted(
            (
                {"section": r["section"], "heading": r["heading"], "pages": json.loads(r["pages"])}
                for r in rows
            ),
            key=lambda s: _section_key(s["section"]),
        )
        if is_invoice:
            inv = invoices.get(name, {})
            file = inv.get("fichero")
            status = "indexed" if inv.get("cuadra") == "1" else "review"
            detail = inv.get("motivo")
            sections = [s for s in sections if s["section"] == "cabecera"] or sections
        else:
            file = f"documents/{name}.pdf"
            status = "indexed" if rows else "no_text"
            detail = None if rows else "PDF sin capa de texto (necesita OCR)"
        out.append(
            {
                "id": doc,
                "kind": "invoice" if is_invoice else "pdf",
                "name": name,
                "title": rows[0]["title"] if rows and not is_invoice else None,
                "n_pages": pages.get(doc, 0),
                "n_chunks": len(rows),
                "sections": sections,
                "added_at": _mtime(cfg.data_dir / file) if file else None,
                "status": status,
                "status_detail": detail,
                "file": file if file and (cfg.data_dir / file).is_file() else None,
            }
        )
    out.sort(key=lambda s: (s["kind"] != "pdf", s["name"].lower()))
    return out


def find_source(cfg: AppConfig, source_id: str) -> dict[str, Any] | None:
    return next((s for s in list_sources(cfg) if s["id"] == source_id), None)


def remove_source(cfg: AppConfig, source: dict[str, Any]) -> None:
    """Drop derived index state; the original file is moved aside, never deleted."""
    store = ChunkStore(cfg.db, cfg.embeddings.dim or 8)
    try:
        store.replace_document(source["id"], [], [], [], commit=False)
        if source["kind"] == "invoice" and _invoice_rows(store.db):
            store.db.execute("DELETE FROM facturas WHERE numero = ?", (source["name"],))
        store.db.commit()
    finally:
        store.db.close()
    if source["file"]:
        src = cfg.data_dir / source["file"]
        removed = cfg.data_dir / "_removed"
        removed.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        shutil.move(str(src), str(removed / f"{stamp}_{src.name}"))


def source_chunks(cfg: AppConfig, source_id: str) -> list[dict[str, Any]]:
    store = ChunkStore(cfg.db, cfg.embeddings.dim)
    try:
        return [
            {
                "chunk_id": row["chunk_id"],
                "section": row["section"],
                "pages": json.loads(row["pages"]),
                "text": row["body"],
            }
            for row in store.db.execute(
                "SELECT chunk_id, section, pages, body FROM chunks WHERE doc = ? ORDER BY rowid",
                (source_id,),
            )
        ]
    finally:
        store.db.close()


def source_page(cfg: AppConfig, doc_id: str, n: int) -> bytes | None:
    store = ChunkStore(cfg.db, cfg.embeddings.dim)
    try:
        png = store.page(doc_id, n)
        if png is None and not doc_id.startswith(("pdf-", "inv-")):
            matches = [
                page
                for key in (pdf_doc_id(doc_id), invoice_doc_id(doc_id))
                if (page := store.page(key, n)) is not None
            ]
            png = matches[0] if len(matches) == 1 else None
        return png
    finally:
        store.db.close()
