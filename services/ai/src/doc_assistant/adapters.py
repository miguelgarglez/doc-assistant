"""Puertos Embedder / Reranker / LLM / OCR: Protocol + HTTP + Fake."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import struct
from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

import requests

from doc_assistant.config import AppConfig


class AdapterError(RuntimeError):
    """Error claro cuando un servidor no responde o falla."""


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


class FakeOCR:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def extract(self, image: bytes) -> str:
        return self.text


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

    def chat_stream(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> Iterator[str]:
        text = json.dumps(self.chat(messages, schema), ensure_ascii=False)
        for i in range(0, len(text), 7):
            yield text[i : i + 7]


class OllamaOCR:
    """Adaptador GLM-OCR vía Ollama (/api/chat con imagen en base64)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "glm-ocr",
        timeout_s: float = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def extract(self, image: bytes) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [
                {
                    "role": "user",
                    "content": "Text Recognition:",
                    "images": [base64.b64encode(image).decode()],
                }
            ],
        }
        data = _request_json("POST", url, timeout=self.timeout_s, json=payload)
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise AdapterError(f"Formato inesperado de OCR en {url}") from e
        if not isinstance(content, str):
            raise AdapterError(f"Contenido OCR no es texto desde {url}")
        return content


class LlamaOCR:
    """Adaptador GLM-OCR GGUF servido por llama-server (/v1/chat/completions con imagen)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8084",
        model: str = "glm-ocr",
        timeout_s: float = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def extract(self, image: bytes) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        b64 = base64.b64encode(image).decode()
        mime = "image/jpeg" if image[:3] == b"\xff\xd8\xff" else "image/png"
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": "Text Recognition:"},
                    ],
                }
            ],
        }
        data = _request_json("POST", url, timeout=self.timeout_s, json=payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise AdapterError(f"Formato inesperado de OCR en {url}") from e
        if not isinstance(content, str):
            raise AdapterError(f"Contenido OCR no es texto desde {url}")
        return content


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
            rows = data["data"]
            if len(rows) != len(texts):
                raise ValueError("incorrect cardinality")
            indices = [row["index"] for row in rows]
            if any(type(i) is not int for i in indices) or sorted(indices) != list(
                range(len(texts))
            ):
                raise ValueError("invalid indices")
            vectors = [row["embedding"] for row in sorted(rows, key=lambda row: row["index"])]
            if any(
                not isinstance(v, list)
                or (self.dim is not None and len(v) != self.dim)
                or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in v)
                for v in vectors
            ):
                raise ValueError("invalid embedding")
            return vectors
        except (KeyError, TypeError, ValueError) as e:
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
            results = data["results"]
            if len(results) != len(documents):
                raise ValueError("incorrect cardinality")
            indices = [x["index"] for x in results]
            if any(type(i) is not int or i < 0 or i >= len(documents) for i in indices) or len(
                set(indices)
            ) != len(indices):
                raise ValueError("invalid rerank indices")
            return sorted(
                ((x["index"], float(x["relevance_score"])) for x in results),
                key=lambda t: -t[1],
            )  # revisión: llama-server no ordena
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
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise AdapterError(f"Contenido LLM no es un objeto JSON desde {self.url}")
            return parsed
        except (TypeError, ValueError) as e:
            raise AdapterError(f"Contenido LLM no es JSON válido desde {self.url}") from e

    def chat_stream(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> Iterator[str]:
        """Yield content deltas from llama-server's OpenAI-compatible SSE stream."""
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema},
            },
            "temperature": 0,
            "stream": True,
        }
        try:
            with requests.post(self.url, json=payload, timeout=self.timeout_s, stream=True) as r:
                r.raise_for_status()
                for raw in r.iter_lines(decode_unicode=False):
                    line = raw.decode("utf-8").strip() if raw else ""
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        delta = json.loads(data)["choices"][0].get("delta") or {}
                    except (ValueError, KeyError, IndexError, TypeError) as e:
                        raise AdapterError(f"Evento de stream inesperado en {self.url}") from e
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
        except requests.Timeout as e:
            raise AdapterError(f"Timeout al contactar {self.url} ({self.timeout_s}s)") from e
        except requests.ConnectionError as e:
            raise AdapterError(f"No responde el servidor en {self.url}") from e
        except requests.HTTPError as e:
            raise AdapterError(f"HTTP {e.response.status_code} en {self.url}") from e


def build_ocr(cfg: AppConfig, *, fake: bool = False, text: str = "") -> OcrPort:
    if fake:
        return FakeOCR(text=text)
    runtime = os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", cfg.ocr.runtime)
    if runtime == "ollama":
        url = cfg.ocr.base_url
        if url.rstrip("/").endswith(":8084"):  # puerto del runtime llama → el de Ollama
            url = "http://127.0.0.1:11434"
        return OllamaOCR(url, cfg.ocr.model, cfg.ocr.timeout_s)
    return LlamaOCR(cfg.ocr.base_url, cfg.ocr.model, cfg.ocr.timeout_s)


def build_adapters(cfg: AppConfig, *, fake: bool = False) -> tuple[Embedder, Reranker, LLM]:
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
