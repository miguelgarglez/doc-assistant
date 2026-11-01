"""Extracción PDF y troceado por secciones numeradas / factura."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber

from doc_assistant.domain.documents.chunking import chunk_pages
from doc_assistant.domain.documents.ids import pdf_doc_id


def extract_pdf_text(path: str | Path) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"n": i, "text": text})
    return pages


def chunk_pdf(path: str | Path, doc: str | None = None) -> list[dict[str, Any]]:
    path = Path(path)
    return chunk_pages(extract_pdf_text(path), doc or pdf_doc_id(path.stem), path.stem)
