from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from doc_assistant.application.ports.models import LLM, Embedder, Reranker
from doc_assistant.application.ports.retrieval import RetrievalIndex
from doc_assistant.application.sources import SourceService


@dataclass(frozen=True)
class AskSettings:
    config_sha256: str
    llm_model: str
    embedding_model: str
    reranker_model: str
    ocr_model: str
    embedding_dim: int
    top_k: int
    answer_mode: str
    inline_citations: str


@dataclass(frozen=True)
class AskContext:
    settings: AskSettings
    sources: Callable[[], SourceService]
    models: Callable[[], tuple[Embedder, Reranker, LLM]]
    ask_invoices: Callable[[str, LLM, dict[str, Any] | None], dict[str, Any] | None]
    retrieval_index: Callable[[int], RetrievalIndex]
