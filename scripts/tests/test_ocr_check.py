import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import OCR_FILES, ocr_problem, ollama_problem


def _serve(models: list[str]) -> tuple[HTTPServer, str]:
    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = json.dumps({"models": [{"name": m} for m in models]}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a: object) -> None:
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def test_ocr_ready_when_model_present() -> None:
    srv, url = _serve(["glm-ocr:latest", "x:1"])
    try:
        assert ollama_problem("/usr/bin/ollama", url) is None
    finally:
        srv.shutdown()


def test_ocr_reports_missing_model() -> None:
    srv, url = _serve(["llama3:8b"])
    try:
        why = ollama_problem("/usr/bin/ollama", url)
        assert why is not None and "ollama pull glm-ocr" in why
    finally:
        srv.shutdown()


def test_ocr_reports_missing_binary_and_server() -> None:
    assert "PATH" in (ollama_problem(None) or "")
    assert "no responde" in (ollama_problem("/usr/bin/ollama", "http://127.0.0.1:1", 0.5) or "")


def test_llama_runtime_ready_when_both_gguf_present(tmp_path: Path) -> None:
    for f in OCR_FILES:
        (tmp_path / f).write_bytes(b"x")
    assert ocr_problem("llama", tmp_path) is None


def test_llama_runtime_reports_missing_mmproj(tmp_path: Path) -> None:
    (tmp_path / OCR_FILES[0]).write_bytes(b"x")
    why = ocr_problem("llama", tmp_path) or ""
    assert OCR_FILES[1] in why and "mise run setup" in why


def test_ollama_runtime_is_the_fallback() -> None:
    assert "PATH" in (ocr_problem("ollama", ollama_path=None) or "")
