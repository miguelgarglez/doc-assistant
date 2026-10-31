"""Puertos Embedder / Reranker / LLM: Protocol + HTTP + Fake."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any, Protocol, runtime_checkable

import requests

from doc_assistant.config import AppConfig


class AdapterError(RuntimeError):
    """Error claro cuando un servidor no responde o falla."""


@runtime_checkable
class OCR(Protocol):
    def extract(self, image: bytes) -> str: ...


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]: ...


@runtime_checkable
class LLM(Protocol):
    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]: ...


class FakeEmbedder:
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            raw = [((digest[i % len(digest)] / 255.0) * 2 - 1) for i in range(self.dim)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            out.append([x / norm for x in raw])
        return out


class FakeReranker:
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        q = query.lower()
        scored = []
        for i, doc in enumerate(documents):
            overlap = sum(1 for tok in q.split() if tok and tok in doc.lower())
            scored.append((i, float(overlap) + (len(documents) - i) * 0.01))
        scored.sort(key=lambda x: -x[1])
        return scored


class FakeLLM:
    def __init__(
        self,
        response: dict[str, Any] | None = None,
        responses: list[dict[str, Any]] | None = None,
    ) -> None:
        self._responses = list(responses) if responses is not None else []
        self._response = response or {
            "answerable": False,
            "answer": None,
            "citations": [],
        }
        self._i = 0

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        if self._responses:
            if self._i >= len(self._responses):
                raise AdapterError("FakeLLM: no quedan respuestas scriptadas")
            out = self._responses[self._i]
            self._i += 1
            return out
        return self._response


def _request_json(method: str, url: str, *, timeout: float, **kwargs: Any) -> Any:
    try:
        r = requests.request(method, url, timeout=timeout, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.Timeout as e:
        raise AdapterError(f"Timeout al contactar {url} ({timeout}s)") from e
    except requests.ConnectionError as e:
        raise AdapterError(f"No responde el servidor en {url}") from e
    except requests.HTTPError as e:
        raise AdapterError(f"HTTP {e.response.status_code} en {url}") from e
    except ValueError as e:
        raise AdapterError(f"Respuesta no JSON desde {url}") from e


class HttpEmbedder:
    def __init__(self, url: str, model: str, timeout_s: float, dim: int | None = None) -> None:
        self.url = url
        self.model = model
        self.timeout_s = timeout_s
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        data = _request_json(
            "POST",
            self.url,
            timeout=self.timeout_s,
            json={"input": texts, "model": self.model},
        )
        try:
            return [row["embedding"] for row in data["data"]]
        except (KeyError, TypeError) as e:
            raise AdapterError(f"Formato inesperado de embeddings en {self.url}") from e


class HttpReranker:
    def __init__(self, url: str, model: str, timeout_s: float) -> None:
        self.url = url
        self.model = model
        self.timeout_s = timeout_s

    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        data = _request_json(
            "POST",
            self.url,
            timeout=self.timeout_s,
            json={"query": query, "documents": documents, "model": self.model},
        )
        try:
            return sorted(((x["index"], float(x["relevance_score"])) for x in data["results"]), key=lambda t: -t[1])  # revisión: llama-server no ordena
        except (KeyError, TypeError, ValueError) as e:
            raise AdapterError(f"Formato inesperado de rerank en {self.url}") from e


class HttpLLM:
    def __init__(self, url: str, model: str, timeout_s: float) -> None:
        self.url = url
        self.model = model
        self.timeout_s = timeout_s

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema},
            },
            "temperature": 0,
        }
        data = _request_json("POST", self.url, timeout=self.timeout_s, json=payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, TypeError, IndexError) as e:
            raise AdapterError(f"Formato inesperado de chat en {self.url}") from e
        if isinstance(content, dict):
            return content
        import json

        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise AdapterError(f"Contenido LLM no es un objeto JSON desde {self.url}")
            return parsed
        except (TypeError, ValueError) as e:
            raise AdapterError(f"Contenido LLM no es JSON válido desde {self.url}") from e


def build_adapters(
    cfg: AppConfig, *, fake: bool = False
) -> tuple[Embedder, Reranker, LLM]:
    if fake:
        dim = cfg.embeddings.dim or 8
        return FakeEmbedder(dim=dim), FakeReranker(), FakeLLM()
    emb = HttpEmbedder(
        cfg.embeddings.url, cfg.embeddings.model, cfg.embeddings.timeout_s, cfg.embeddings.dim
    )
    rr = HttpReranker(cfg.reranker.url, cfg.reranker.model, cfg.reranker.timeout_s)
    llm = HttpLLM(cfg.llm.url, cfg.llm.model, cfg.llm.timeout_s)
    return emb, rr, llm


def serialize_f32(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)
