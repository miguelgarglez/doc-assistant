"""Ingestión de PDFs y facturas → SQLite (idempotente)."""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

from doc_assistant.adapters import Embedder, build_adapters
from doc_assistant.chunking import chunk_invoice, chunk_pdf, pdf_doc_id
from doc_assistant.config import load_config
from doc_assistant.pdf_lock import pdf_lock
from doc_assistant.store import ChunkStore


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_pdf_filename(name: str) -> str:
    base = Path(name or "document.pdf").name
    safe = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._") or "document"
    if not safe.lower().endswith(".pdf"):
        safe = f"{safe}.pdf"
    return safe


def find_pdf_by_hash(directory: Path, digest: str) -> Path | None:
    if not directory.is_dir():
        return None
    for pdf in sorted(directory.glob("*.pdf")):
        if content_hash(pdf.read_bytes()) == digest:
            return pdf
    return None


def ingest_pdfs(
    config_path: str | Path,
    pdf_dir: str | Path,
    *,
    invoice_path: str | Path | None = None,
    image_path: str | Path | None = None,  # reservado; no OCR en esta rebanada
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    report = progress or (lambda *_args, **_kwargs: None)
    cfg = load_config(config_path)
    pdf_dir = Path(pdf_dir)

    if embedder is None:
        embedder, _, _ = build_adapters(cfg, fake=False)

    dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
    store = ChunkStore(cfg.db, dim=dim)

    all_chunks: list[dict[str, Any]] = []
    warnings: list[str] = []
    if pdf_dir.is_file() and pdf_dir.suffix.lower() == ".pdf":
        pdfs = [pdf_dir]
    elif pdf_dir.is_dir():
        pdfs = sorted(pdf_dir.glob("*.pdf"))
        for other in sorted(pdf_dir.iterdir()):
            if (
                other.is_file()
                and other.suffix.lower() != ".pdf"
                and not other.name.startswith(".")
            ):
                warnings.append(f"ignorado (tipo no soportado): {other.name}")
    else:
        pdfs = []
    seen_hashes: dict[str, str] = {}
    documents: list[tuple[str, list[dict[str, Any]], list[bytes]]] = []
    t_extract = time.perf_counter()
    report("reading")
    for pdf in pdfs:
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest in seen_hashes:
            warnings.append(f"duplicado de {seen_hashes[digest]}, no se indexa: {pdf.name}")
            continue
        seen_hashes[digest] = pdf.name
        try:
            chunks = chunk_pdf(pdf)
        except Exception as exc:  # noqa: BLE001 — isolate malformed PDFs
            warnings.append(f"no se pudo leer {pdf.name}: {type(exc).__name__}")
            continue
        if not chunks:
            warnings.append(f"sin capa de texto (necesita OCR), no se indexa: {pdf.name}")
        try:
            with pdf_lock:
                pdf_document = pdfium.PdfDocument(pdf)
                try:
                    images = []
                    total_pages = len(pdf_document)
                    for page_number, page in enumerate(pdf_document, 1):
                        try:
                            bitmap = page.render(scale=2)
                            try:
                                image = bitmap.to_pil()
                                output = io.BytesIO()
                                image.save(output, format="PNG")
                                images.append(output.getvalue())
                            finally:
                                bitmap.close()
                        finally:
                            page.close()
                        report("reading", current=page_number, total=total_pages)
                finally:
                    pdf_document.close()
        except Exception as exc:  # noqa: BLE001 — isolate rendering failures
            warnings.append(f"no se pudo renderizar {pdf.name}: {type(exc).__name__}")
            continue
        documents.append((pdf_doc_id(pdf.stem), chunks, images))
        all_chunks.extend(chunks)
    extract_s = time.perf_counter() - t_extract

    paths = (
        invoice_path
        if isinstance(invoice_path, (list, tuple))
        else [invoice_path]
        if invoice_path
        else []
    )
    for one in paths:
        data = json.loads(Path(one).read_text(encoding="utf-8"))
        all_chunks.extend(chunk_invoice(data))
        # image_path is accepted for CLI parity; content comes from JSON fields.

    if not all_chunks and not documents:
        return {
            "n_chunks": 0,
            "chunk_ids": [],
            "warnings": warnings,
            "timings": {
                "extract_s": extract_s,
                "embed_s": 0.0,
                "store_s": 0.0,
                "total_s": time.perf_counter() - t0,
            },
        }

    report("indexing")
    t_emb = time.perf_counter()
    embeddings = []
    for start in range(0, len(all_chunks), 32):
        batch = all_chunks[start : start + 32]
        embeddings.extend(embedder.embed([c["text"] for c in batch]))
        report("indexing", current=min(start + len(batch), len(all_chunks)), total=len(all_chunks))
    embed_s = time.perf_counter() - t_emb

    t_store = time.perf_counter()
    offset = 0
    for doc, chunks, pages in documents:
        store.replace_document(doc, chunks, embeddings[offset : offset + len(chunks)], pages)
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


def save_and_ingest_pdf(
    config_path: str | Path,
    data: bytes,
    filename: str,
    *,
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Save a PDF under data_dir/documents (sanitized name) and ingest it.

    Idempotent by content hash: an existing file with the same bytes is reused.
    """
    cfg = load_config(config_path)
    docs_dir = cfg.data_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    digest = content_hash(data)
    existing = find_pdf_by_hash(docs_dir, digest)
    if existing is not None:
        path = existing
        created = False
    else:
        path = docs_dir / sanitize_pdf_filename(filename)
        if path.exists() and content_hash(path.read_bytes()) != digest:
            path = docs_dir / f"{digest[:12]}_{sanitize_pdf_filename(filename)}"
        path.write_bytes(data)
        created = True
    result = ingest_pdfs(config_path, path, embedder=embedder, progress=progress)
    result["doc_id"] = pdf_doc_id(path.stem)
    result["path"] = str(path.relative_to(cfg.data_dir))
    result["content_hash"] = digest
    result["created"] = created
    return result
