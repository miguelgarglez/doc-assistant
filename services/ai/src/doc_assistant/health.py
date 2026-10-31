"""Per-component health: one cheap probe per dependency, measured in parallel."""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from urllib.parse import urlparse

import requests
from pydantic import BaseModel

from doc_assistant.config import AppConfig

ComponentId = Literal["ai", "llm", "embeddings", "reranker", "ocr", "sqlite"]
ComponentStatus = Literal["ok", "degraded", "unavailable"]

PROBE_TIMEOUT_S = 2.0


class ComponentHealth(BaseModel):
    id: ComponentId
    status: ComponentStatus
    latency_ms: float | None = None
    detail: str | None = None


class ComponentsHealth(BaseModel):
    components: list[ComponentHealth]


def _host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url


def probe_llama(
    component: ComponentId, base_url: str, health_path: str = "/health"
) -> ComponentHealth:
    """llama-server answers 200 when ready and 503 while the model loads."""
    url = base_url.rstrip("/") + health_path
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=PROBE_TIMEOUT_S)
    except requests.Timeout:
        return ComponentHealth(
            id=component, status="degraded", detail=f"{_host(base_url)} no responde a tiempo"
        )
    except requests.RequestException:
        return ComponentHealth(
            id=component, status="unavailable", detail=f"{_host(base_url)} no está en marcha"
        )
    latency = round((time.perf_counter() - started) * 1000, 1)
    if response.status_code == 200:
        return ComponentHealth(
            id=component, status="ok", latency_ms=latency, detail=_host(base_url)
        )
    if response.status_code == 503:
        return ComponentHealth(
            id=component,
            status="degraded",
            latency_ms=latency,
            detail=f"{_host(base_url)} cargando el modelo",
        )
    return ComponentHealth(
        id=component,
        status="degraded",
        latency_ms=latency,
        detail=f"{_host(base_url)} respondió HTTP {response.status_code}",
    )


def probe_index(cfg: AppConfig) -> ComponentHealth:
    """Read-only connection: a health check must never create or migrate the index."""
    if not cfg.db.is_file():
        return ComponentHealth(id="sqlite", status="degraded", detail="Índice aún sin crear")
    started = time.perf_counter()
    try:
        con = sqlite3.connect(f"file:{cfg.db}?mode=ro", uri=True, timeout=PROBE_TIMEOUT_S)
        try:
            row = con.execute("SELECT count(*) FROM chunks").fetchone()
        finally:
            con.close()
    except sqlite3.Error as error:
        return ComponentHealth(id="sqlite", status="unavailable", detail=str(error)[:120])
    latency = round((time.perf_counter() - started) * 1000, 1)
    count = int(row[0])
    return ComponentHealth(
        id="sqlite",
        status="ok",
        latency_ms=latency,
        detail=f"{count} fragmentos" if count else "Índice vacío",
    )


def _ocr_probe(cfg: AppConfig) -> Callable[[], ComponentHealth]:
    runtime = os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", cfg.ocr.runtime)
    if runtime == "ollama":
        url = cfg.ocr.base_url
        if url.rstrip("/").endswith(":8084"):
            url = "http://127.0.0.1:11434"
        return lambda: probe_llama("ocr", url, "/api/version")
    return lambda: probe_llama("ocr", cfg.ocr.base_url)


def check_components(cfg: AppConfig) -> ComponentsHealth:
    probes: list[Callable[[], ComponentHealth]] = [
        lambda: probe_llama("llm", cfg.llm.base_url),
        lambda: probe_llama("embeddings", cfg.embeddings.base_url),
        lambda: probe_llama("reranker", cfg.reranker.base_url),
        _ocr_probe(cfg),
        lambda: probe_index(cfg),
    ]
    with ThreadPoolExecutor(max_workers=len(probes)) as pool:
        results = list(pool.map(lambda probe: probe(), probes))
    own = ComponentHealth(id="ai", status="ok", detail="Responde")
    return ComponentsHealth(components=[own, *results])
