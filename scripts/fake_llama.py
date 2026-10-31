"""Simulador mínimo de llama-server para CI (sin modelo): /health, chat, embeddings, rerank."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self._send({"status": "ok"})

    def do_POST(self) -> None:
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path.endswith("/embeddings"):
            inputs = req.get("input", [])
            inputs = inputs if isinstance(inputs, list) else [inputs]
            self._send(
                {"data": [{"index": i, "embedding": [0.0] * 1024} for i in range(len(inputs))]}
            )
        elif self.path.endswith("/rerank"):
            self._send(
                {
                    "results": [
                        {"index": i, "relevance_score": 0.0}
                        for i in range(len(req.get("documents", [])))
                    ]
                }
            )
        else:
            self._send({"choices": [{"message": {"role": "assistant", "content": "NO_SE"}}]})

    def log_message(self, *_: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    a, _ = ap.parse_known_args()
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
