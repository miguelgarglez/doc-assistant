import base64
import json
import math
from collections.abc import Iterator
from typing import Any

import requests

from doc_assistant.application.ports.models import AdapterBusy, AdapterError, AdapterTimeout


def http_adapter_error(error: requests.HTTPError, url: str) -> AdapterError:
    status = error.response.status_code
    detail = f"HTTP {status} en {url}"
    return AdapterBusy(detail) if status in (429, 503) else AdapterError(detail)


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
        raise AdapterTimeout(f"Timeout al contactar {url} ({timeout}s)") from e
    except requests.ConnectionError as e:
        raise AdapterBusy(f"No responde el servidor en {url}") from e
    except requests.HTTPError as e:
        raise http_adapter_error(e, url) from e
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
            raise AdapterTimeout(f"Timeout al contactar {self.url} ({self.timeout_s}s)") from e
        except requests.ConnectionError as e:
            raise AdapterError(f"No responde el servidor en {self.url}") from e
        except requests.HTTPError as e:
            raise http_adapter_error(e, self.url) from e
