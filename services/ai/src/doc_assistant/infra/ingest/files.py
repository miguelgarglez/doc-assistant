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

from doc_assistant.application.ports.ingest import (
    IngestBatch,
    IngestDocument,
    StoredPdf,
)
from doc_assistant.domain.documents.ids import pdf_doc_id
from doc_assistant.domain.invoices.chunking import chunk_invoice
from doc_assistant.infra.pdf.extract import chunk_pdf
from doc_assistant.infra.pdf.lock import pdf_lock


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


class FileIngestReader:
    def read(
        self,
        pdf_source: str | Path,
        *,
        invoice_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None,
        progress: Callable[..., None],
    ) -> IngestBatch:
        source = Path(pdf_source)
        warnings: list[str] = []
        if source.is_file() and source.suffix.lower() == ".pdf":
            pdfs = [source]
        elif source.is_dir():
            pdfs = sorted(source.glob("*.pdf"))
            for other in sorted(source.iterdir()):
                if (
                    other.is_file()
                    and other.suffix.lower() != ".pdf"
                    and not other.name.startswith(".")
                ):
                    warnings.append(f"ignorado (tipo no soportado): {other.name}")
        else:
            pdfs = []

        chunks: list[dict[str, Any]] = []
        documents: list[IngestDocument] = []
        seen_hashes: dict[str, str] = {}
        extraction_started = time.perf_counter()
        progress("reading")
        for pdf in pdfs:
            digest = content_hash(pdf.read_bytes())
            if digest in seen_hashes:
                warnings.append(f"duplicado de {seen_hashes[digest]}, no se indexa: {pdf.name}")
                continue
            seen_hashes[digest] = pdf.name
            try:
                pdf_chunks = chunk_pdf(pdf)
            except Exception as exc:  # noqa: BLE001 — isolate malformed PDFs
                warnings.append(f"no se pudo leer {pdf.name}: {type(exc).__name__}")
                continue
            if not pdf_chunks:
                warnings.append(f"sin capa de texto (necesita OCR), no se indexa: {pdf.name}")
            try:
                pages = self._render(pdf, progress)
            except Exception as exc:  # noqa: BLE001 — isolate rendering failures
                warnings.append(f"no se pudo renderizar {pdf.name}: {type(exc).__name__}")
                continue
            documents.append(
                IngestDocument(
                    doc=pdf_doc_id(pdf.stem),
                    chunks=pdf_chunks,
                    pages=pages,
                )
            )
            chunks.extend(pdf_chunks)

        extract_s = time.perf_counter() - extraction_started
        invoice_paths = (
            list(invoice_path)
            if isinstance(invoice_path, (list, tuple))
            else [invoice_path]
            if invoice_path
            else []
        )
        for path in invoice_paths:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            chunks.extend(chunk_invoice(data))
        return IngestBatch(
            chunks=chunks, documents=documents, warnings=warnings, extract_s=extract_s
        )

    @staticmethod
    def _render(path: Path, progress: Callable[..., None]) -> list[bytes]:
        with pdf_lock:
            document = pdfium.PdfDocument(path)
            try:
                pages: list[bytes] = []
                total_pages = len(document)
                for page_number, page in enumerate(document, 1):
                    try:
                        bitmap = page.render(scale=2)
                        try:
                            image = bitmap.to_pil()
                            output = io.BytesIO()
                            image.save(output, format="PNG")
                            pages.append(output.getvalue())
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                    progress("reading", current=page_number, total=total_pages)
                return pages
            finally:
                document.close()


class DataDirectoryPdfFiles:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def save(self, data: bytes, filename: str) -> StoredPdf:
        documents = self.data_dir / "documents"
        documents.mkdir(parents=True, exist_ok=True)
        digest = content_hash(data)
        existing = find_pdf_by_hash(documents, digest)
        if existing is not None:
            path = existing
            created = False
        else:
            path = documents / sanitize_pdf_filename(filename)
            if path.exists() and content_hash(path.read_bytes()) != digest:
                path = documents / f"{digest[:12]}_{sanitize_pdf_filename(filename)}"
            path.write_bytes(data)
            created = True
        return StoredPdf(
            path=path,
            relative_path=str(path.relative_to(self.data_dir)),
            digest=digest,
            created=created,
        )
