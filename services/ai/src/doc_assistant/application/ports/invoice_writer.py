from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class InvoiceWrite:
    number: str
    record: dict[str, Any]
    state: str
    reason: str | None
    filename: str
    image: bytes
    chunks: list[dict[str, Any]]
    embeddings: list[list[float]]


class InvoiceWriter(Protocol):
    def save(self, invoice: InvoiceWrite) -> str: ...
