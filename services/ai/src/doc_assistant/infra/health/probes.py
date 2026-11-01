import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from doc_assistant.application.ports.health import ComponentId, ProbeResult

PROBE_TIMEOUT_S = 2.0


def _host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url


def probe_llama(component: ComponentId, base_url: str, health_path: str = "/health") -> ProbeResult:
    url = base_url.rstrip("/") + health_path
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=PROBE_TIMEOUT_S)
    except requests.Timeout:
        return ProbeResult(
            id=component, status="degraded", detail=f"{_host(base_url)} no responde a tiempo"
        )
    except requests.RequestException:
        return ProbeResult(
            id=component, status="unavailable", detail=f"{_host(base_url)} no está en marcha"
        )
    latency = round((time.perf_counter() - started) * 1000, 1)
    if response.status_code == 200:
        return ProbeResult(id=component, status="ok", latency_ms=latency, detail=_host(base_url))
    if response.status_code == 503:
        return ProbeResult(
            id=component,
            status="degraded",
            latency_ms=latency,
            detail=f"{_host(base_url)} cargando el modelo",
        )
    return ProbeResult(
        id=component,
        status="degraded",
        latency_ms=latency,
        detail=f"{_host(base_url)} respondió HTTP {response.status_code}",
    )


def probe_index(path: Path) -> ProbeResult:
    if not path.is_file():
        return ProbeResult(id="sqlite", status="degraded", detail="Índice aún sin crear")
    started = time.perf_counter()
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=PROBE_TIMEOUT_S)
        try:
            row = connection.execute("SELECT count(*) FROM chunks").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as error:
        return ProbeResult(id="sqlite", status="unavailable", detail=str(error)[:120])
    latency = round((time.perf_counter() - started) * 1000, 1)
    count = int(row[0])
    return ProbeResult(
        id="sqlite",
        status="ok",
        latency_ms=latency,
        detail=f"{count} fragmentos" if count else "Índice vacío",
    )
