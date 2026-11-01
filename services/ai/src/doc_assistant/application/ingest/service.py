from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from doc_assistant.application.ports.ingest import (
    IngestReader,
    IngestWriter,
    IngestWriterFactory,
    PdfFiles,
)
from doc_assistant.application.ports.models import Embedder
from doc_assistant.domain.documents.ids import pdf_doc_id


class IngestService:
    def __init__(
        self,
        reader: IngestReader,
        writer_factory: IngestWriterFactory,
        files: PdfFiles,
        default_dim: int,
    ) -> None:
        self.reader = reader
        self.writer_factory = writer_factory
        self.files = files
        self.default_dim = default_dim

    def ingest(
        self,
        pdf_source: str | Path,
        *,
        embedder: Embedder,
        started: float,
        invoice_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
        progress: Callable[..., None] | None = None,
    ) -> dict[str, Any]:
        dim = getattr(embedder, "dim", None) or self.default_dim or 8
        with self.writer_factory(dim) as writer:
            return self._ingest(pdf_source, embedder, invoice_path, progress, writer, started)

    def _ingest(
        self,
        pdf_source: str | Path,
        embedder: Embedder,
        invoice_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None,
        progress: Callable[..., None] | None,
        writer: IngestWriter,
        started: float,
    ) -> dict[str, Any]:
        report = progress or (lambda *_args, **_kwargs: None)
        batch = self.reader.read(
            pdf_source,
            invoice_path=invoice_path,
            progress=report,
        )
        extract_s = batch.extract_s

        if not batch.chunks and not batch.documents:
            return {
                "n_chunks": 0,
                "chunk_ids": [],
                "warnings": batch.warnings,
                "timings": {
                    "extract_s": extract_s,
                    "embed_s": 0.0,
                    "store_s": 0.0,
                    "total_s": time.perf_counter() - started,
                },
            }

        report("indexing")
        embedding_started = time.perf_counter()
        embeddings: list[list[float]] = []
        for start in range(0, len(batch.chunks), 32):
            chunks = batch.chunks[start : start + 32]
            embeddings.extend(embedder.embed([chunk["text"] for chunk in chunks]))
            report(
                "indexing",
                current=min(start + len(chunks), len(batch.chunks)),
                total=len(batch.chunks),
            )
        embed_s = time.perf_counter() - embedding_started

        store_started = time.perf_counter()
        offset = 0
        for document in batch.documents:
            writer.replace_document(
                document.doc,
                document.chunks,
                embeddings[offset : offset + len(document.chunks)],
                document.pages,
            )
            offset += len(document.chunks)
        if offset < len(batch.chunks):
            writer.upsert(batch.chunks[offset:], embeddings[offset:])
        store_s = time.perf_counter() - store_started

        return {
            "n_chunks": len(batch.chunks),
            "chunk_ids": sorted(chunk["chunk_id"] for chunk in batch.chunks),
            "warnings": batch.warnings,
            "timings": {
                "extract_s": round(extract_s, 4),
                "embed_s": round(embed_s, 4),
                "store_s": round(store_s, 4),
                "total_s": round(time.perf_counter() - started, 4),
            },
        }

    def save_and_ingest(
        self,
        data: bytes,
        filename: str,
        *,
        ingest: Callable[[Path], dict[str, Any]],
    ) -> dict[str, Any]:
        stored = self.files.save(data, filename)
        result = ingest(stored.path)
        result["doc_id"] = pdf_doc_id(stored.path.stem)
        result["path"] = stored.relative_path
        result["content_hash"] = stored.digest
        result["created"] = stored.created
        return result
