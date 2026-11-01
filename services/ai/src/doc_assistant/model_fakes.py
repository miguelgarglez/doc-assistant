import hashlib
import json
import math
from collections.abc import Iterator
from typing import Any

from doc_assistant.model_ports import AdapterError


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
