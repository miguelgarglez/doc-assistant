from dataclasses import dataclass
from typing import Literal, Protocol

ComponentId = Literal["ai", "llm", "embeddings", "reranker", "ocr", "sqlite"]
ComponentStatus = Literal["ok", "degraded", "unavailable"]


@dataclass(frozen=True)
class ProbeResult:
    id: ComponentId
    status: ComponentStatus
    latency_ms: float | None = None
    detail: str | None = None


class ComponentProbe(Protocol):
    def __call__(self) -> ProbeResult: ...
