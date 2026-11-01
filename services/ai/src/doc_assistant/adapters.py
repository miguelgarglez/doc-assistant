import os

from doc_assistant.application.ports.models import LLM, Embedder, OcrPort, Reranker
from doc_assistant.config import AppConfig
from doc_assistant.infra.models.http import HttpEmbedder, HttpLLM, HttpReranker, LlamaOCR, OllamaOCR
from doc_assistant.model_fakes import FakeEmbedder, FakeLLM, FakeOCR, FakeReranker


def build_ocr(cfg: AppConfig, *, fake: bool = False, text: str = "") -> OcrPort:
    if fake:
        return FakeOCR(text=text)
    runtime = os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", cfg.ocr.runtime)
    if runtime == "ollama":
        return OllamaOCR(cfg.ocr.ollama_url(), cfg.ocr.model, cfg.ocr.timeout_s)
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
