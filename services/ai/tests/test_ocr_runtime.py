"""OCR por defecto en llama-server (GLM-OCR GGUF) y Ollama como alternativa."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from doc_assistant.bootstrap import build_ocr
from doc_assistant.config import load_config
from doc_assistant.infra.models.http import LlamaOCR, OllamaOCR

ROOT = Path(__file__).resolve().parents[3]


def test_repo_config_uses_llama_runtime_on_8084(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOC_ASSISTANT_OCR_RUNTIME", raising=False)
    cfg = load_config(ROOT / "config" / "config.yaml")
    ocr = build_ocr(cfg)
    assert isinstance(ocr, LlamaOCR) and ocr.base_url == "http://127.0.0.1:8084"


def test_env_switches_to_ollama_fallback_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOC_ASSISTANT_OCR_RUNTIME", "ollama")
    ocr = build_ocr(load_config(ROOT / "config" / "config.yaml"))
    assert isinstance(ocr, OllamaOCR) and ocr.base_url == "http://127.0.0.1:11434"


def test_llama_ocr_sends_image_and_prompt() -> None:
    seen: dict = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            seen["path"] = self.path
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            out = json.dumps({"choices": [{"message": {"content": "FACTURA 1"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a: object) -> None:
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        text = LlamaOCR(f"http://127.0.0.1:{srv.server_port}").extract(b"\x89PNG....")
    finally:
        srv.shutdown()
    assert text == "FACTURA 1"
    assert seen["path"] == "/v1/chat/completions"
    parts = seen["body"]["messages"][0]["content"]
    assert parts[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert parts[1]["text"] == "Text Recognition:"
