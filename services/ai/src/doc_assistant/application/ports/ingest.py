from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class IngestDocument:
    doc: str
    chunks: list[dict[str, Any]]
    pages: list[bytes]


@dataclass(frozen=True)
class IngestBatch:
    chunks: list[dict[str, Any]]
    documents: list[IngestDocument]
    warnings: list[str]
    extract_s: float


@dataclass(frozen=True)
class StoredPdf:
    path: Path
    relative_path: str
    digest: str
    created: bool


class IngestReader(Protocol):
    def read(
        self,
        pdf_source: str | Path,
        *,
        invoice_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None,
        progress: Callable[..., None],
    ) -> IngestBatch: ...


class IngestWriter(Protocol):
    def replace_document(
        self,
        doc: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        pages: list[bytes],
    ) -> None: ...

    def upsert(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None: ...


class IngestWriterFactory(Protocol):
    def __call__(self, dim: int) -> AbstractContextManager[IngestWriter]: ...


class PdfFiles(Protocol):
    def save(self, data: bytes, filename: str) -> StoredPdf: ...
