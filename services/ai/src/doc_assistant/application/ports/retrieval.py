from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RetrievalResult:
    vector_scores: list[tuple[str, float]]
    keyword_scores: list[tuple[str, float]]
    chunks: dict[str, dict[str, Any]]
    index_sha256: str | None
    schema_version: int | None


class RetrievalIndex(Protocol):
    def search(
        self, embedding: list[float], question: str, *, fingerprint: bool
    ) -> RetrievalResult: ...
