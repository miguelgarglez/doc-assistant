from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """Error claro cuando un servidor no responde o falla."""

    code = "adapter_error"

    @property
    def public_message(self) -> str:
        return str(self)


class AdapterBusy(AdapterError):
    code = "model_busy"

    @property
    def public_message(self) -> str:
        return "El modelo está ocupado o no está disponible. Inténtalo de nuevo en unos segundos."


class AdapterTimeout(AdapterError):
    code = "model_timeout"

    @property
    def public_message(self) -> str:
        return "El modelo tardó demasiado en responder. Inténtalo de nuevo."


@runtime_checkable
class OcrPort(Protocol):
    def extract(self, image: bytes) -> str: ...


OCR = OcrPort


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]: ...


@runtime_checkable
class LLM(Protocol):
    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class StreamingLLM(LLM, Protocol):
    def chat_stream(
        self, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> Iterator[str]: ...
