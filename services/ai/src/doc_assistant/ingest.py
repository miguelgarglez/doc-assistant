"""Ingestión de PDFs y facturas → SQLite (idempotente)."""

from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

from doc_assistant.adapters import Embedder, build_adapters
from doc_assistant.chunking import chunk_invoice, chunk_pdf
from doc_assistant.config import load_config
from doc_assistant.store import ChunkStore


def ingest_pdfs(
    config_path: str | Path,
    pdf_dir: str | Path,
    *,
    invoice_path: str | Path | None = None,
    image_path: str | Path | None = None,  # reservado; no OCR en esta rebanada
    embedder: Embedder | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    cfg = load_config(config_path)
    pdf_dir = Path(pdf_dir)

    if embedder is None:
        embedder, _, _ = build_adapters(cfg, fake=False)

    dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
    store = ChunkStore(cfg.db, dim=dim)

    all_chunks: list[dict[str, Any]] = []
    pdfs = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.is_dir() else []
    warnings: list[str] = []
    if pdf_dir.is_dir():
        for other in sorted(pdf_dir.iterdir()):
            if other.is_file() and other.suffix.lower() != ".pdf" and not other.name.startswith("."):
                warnings.append(f"ignorado (tipo no soportado): {other.name}")
    seen_hashes: dict[str, str] = {}
    documents: list[tuple[str, list[dict[str, Any]], list[bytes]]] = []
    t_extract = time.perf_counter()
    for pdf in pdfs:
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest in seen_hashes:
            warnings.append(f"duplicado de {seen_hashes[digest]}, no se indexa: {pdf.name}")
            continue
        seen_hashes[digest] = pdf.name
        try:
            chunks = chunk_pdf(pdf, doc=pdf.stem)
        except Exception as exc:  # noqa: BLE001 — isolate malformed PDFs
            warnings.append(f"no se pudo leer {pdf.name}: {type(exc).__name__}")
            continue
        if not chunks:
            warnings.append(f"sin capa de texto (necesita OCR), no se indexa: {pdf.name}")
        try:
            pdf_document = pdfium.PdfDocument(pdf)
            images = []
            for page in pdf_document:
                image = page.render(scale=2).to_pil()
                output = io.BytesIO()
                image.save(output, format="PNG")
                images.append(output.getvalue())
            pdf_document.close()
        except Exception as exc:  # noqa: BLE001 — isolate rendering failures
            warnings.append(f"no se pudo renderizar {pdf.name}: {type(exc).__name__}")
            continue
        documents.append((pdf.stem, chunks, images))
        all_chunks.extend(chunks)
    extract_s = time.perf_counter() - t_extract

    paths = invoice_path if isinstance(invoice_path, (list, tuple)) else [invoice_path] if invoice_path else []
    for one in paths:
        data = json.loads(Path(one).read_text(encoding="utf-8"))
        all_chunks.extend(chunk_invoice(data))
        # image_path is accepted for CLI parity; content comes from JSON fields.

    if not all_chunks and not documents:
        return {
            "n_chunks": 0,
            "chunk_ids": [],
            "warnings": warnings,
            "timings": {"extract_s": extract_s, "embed_s": 0.0, "store_s": 0.0, "total_s": time.perf_counter() - t0},
        }

    t_emb = time.perf_counter()
    # Batch to keep Fake/HTTP simple
    embeddings = embedder.embed([c["text"] for c in all_chunks]) if all_chunks else []
    embed_s = time.perf_counter() - t_emb

    t_store = time.perf_counter()
    offset = 0
    for doc, chunks, pages in documents:
        store.replace_document(doc, chunks, embeddings[offset:offset + len(chunks)], pages)
        offset += len(chunks)
    if offset < len(all_chunks):
        store.upsert(all_chunks[offset:], embeddings[offset:])
    store_s = time.perf_counter() - t_store

    ids = sorted(c["chunk_id"] for c in all_chunks)
    return {
        "n_chunks": len(all_chunks),
        "chunk_ids": ids,
        "warnings": warnings,
        "timings": {
            "extract_s": round(extract_s, 4),
            "embed_s": round(embed_s, 4),
            "store_s": round(store_s, 4),
            "total_s": round(time.perf_counter() - t0, 4),
        },
    }
