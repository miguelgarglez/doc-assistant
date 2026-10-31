"""SSE /ask/stream, preguntas meta y catálogo de fuentes."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from doc_assistant import ask as ask_module
from doc_assistant.adapters import AdapterError, FakeEmbedder, FakeLLM, FakeReranker, HttpLLM
from doc_assistant.api import create_app
from doc_assistant.config import load_config
from doc_assistant.ingest import save_and_ingest_pdf
from doc_assistant.meta import classify
from doc_assistant.partial_json import FieldStreamer
from doc_assistant.sources import list_sources
from doc_assistant.store import ChunkStore

ROOT = Path(__file__).resolve().parents[3]


def events(body: str) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def seed(config_path: Path, synthetic_pdf: Path) -> dict[str, Any]:
    return save_and_ingest_pdf(
        config_path, synthetic_pdf.read_bytes(), "ACME-100.pdf", embedder=FakeEmbedder()
    )


def use_fakes(monkeypatch: pytest.MonkeyPatch, llm: Any) -> None:
    monkeypatch.setattr(
        ask_module, "build_adapters", lambda cfg, fake=False: (FakeEmbedder(), FakeReranker(), llm)
    )


def chunk_for(config_path: Path, section: str) -> dict[str, Any]:
    store = ChunkStore(load_config(config_path).db, 8)
    try:
        return store.get_by_section(section)
    finally:
        store.db.close()


def stream(config_path: Path, question: str) -> list[tuple[str, dict[str, Any]]]:
    with TestClient(create_app(config_path)) as client:
        r = client.post("/ask/stream", json={"question": question})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        return events(r.text)


def test_field_streamer_decodes_answer_in_any_split() -> None:
    obj = {
        "citations": [{"quote": '"answer": no'}],
        "answer": 'A "b" \u00e9\nc',
        "answerable": True,
    }
    text = json.dumps(obj)
    for size in (1, 2, 5, 64):
        f = FieldStreamer("answer")
        assert (
            "".join(f.feed(text[i : i + size]) for i in range(0, len(text), size)) == obj["answer"]
        )
    assert FieldStreamer("answer").feed('{"answerable":false,"answer":null}') == ""


def test_stream_verified_answer(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)
    chunk = chunk_for(config_path, "1")
    answer = "El robot debe operar a 24 V."
    use_fakes(
        monkeypatch,
        FakeLLM(
            {
                "answerable": True,
                "answer": answer,
                "citations": [{"chunk_id": chunk["chunk_id"], "quote": "24 V"}],
            }
        ),
    )
    evs = stream(config_path, "¿A qué voltaje opera el robot?")
    kinds = [k for k, _ in evs]
    assert kinds[-2:] == ["citations", "done"]
    assert "".join(d["text"] for k, d in evs if k == "token") == answer
    steps = [(d["id"], d["status"]) for k, d in evs if k == "step"]
    for sid in ("route", "retrieve", "rerank", "generate", "verify"):
        assert (sid, "running") in steps and (sid, "done") in steps
    done = evs[-1][1]
    assert done["ok"] is True and done["answer"] == answer and done["reason"] == "verified"
    assert done["timings"]["total"] >= 0
    # Los tokens solo llegan después de recuperar: nunca antes de tener fragmentos.
    assert kinds.index("token") > steps.index(("rerank", "done"))


def test_stream_retracts_answer_that_fails_verification(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)
    chunk = chunk_for(config_path, "1")
    use_fakes(
        monkeypatch,
        FakeLLM(
            {
                "answerable": True,
                "answer": "Opera a 48 V.",
                "citations": [{"chunk_id": chunk["chunk_id"], "quote": "24 V"}],
            }
        ),
    )
    evs = stream(config_path, "¿A qué voltaje opera el robot?")
    assert any(k == "token" for k, _ in evs)
    assert "citations" not in [k for k, _ in evs]
    kind, refusal = evs[-2]
    assert kind == "refusal" and refusal["retract"] is True
    assert refusal["reason"].startswith("verify:")
    assert refusal["suggestions"] and refusal["suggestions"][0]["doc"] == "ACME-100"
    assert evs[-1][1]["ok"] is False and "48" not in evs[-1][1]["answer"]


def test_stream_refusal_without_tokens_does_not_retract(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)
    use_fakes(monkeypatch, FakeLLM())
    evs = stream(config_path, "¿Cuánto cuesta el robot?")
    assert [k for k, _ in evs if k == "token"] == []
    assert evs[-2][0] == "refusal" and evs[-2][1]["retract"] is False


def test_stream_adapter_failure_ends_with_error(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)

    class Broken(FakeLLM):
        def chat_stream(self, messages: Any, schema: Any) -> Any:
            yield '{"answerable": true, "answer": "Op'
            raise AdapterError("No responde el servidor en x")

    use_fakes(monkeypatch, Broken())
    evs = stream(config_path, "¿A qué voltaje opera el robot?")
    assert evs[-1] == (
        "error",
        {"code": "adapter_error", "message": "No responde el servidor en x"},
    )
    assert "done" not in [k for k, _ in evs]


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("¿Qué sabes hacer?", "capabilities"),
        ("¿En qué me puedes ayudar?", "capabilities"),
        ("¿Qué tipo de preguntas puedo hacerte?", "capabilities"),
        ("¿Qué documentos tienes?", "inventory"),
        ("Resúmeme lo que hay", "inventory"),
        ("¿Qué fuentes hay indexadas?", "inventory"),
        ("¿De qué trata el ACME-100?", "document"),
        ("Hazme un resumen del acme 100", "document"),
        # Trampas: sin documento reconocible o pregunta de contenido → pipeline normal.
        ("¿Qué sabes del precio del robot?", "rag"),
        ("¿De qué trata el documento de garantías?", "rag"),
        ("Resúmeme el manual del modelo X999", "rag"),
        ("¿Qué documentos dicen que el sensor alcanza 20 m?", "rag"),
        ("¿A qué voltaje opera el robot?", "rag"),
    ],
)
def test_classify(config_path: Path, synthetic_pdf: Path, question: str, intent: str) -> None:
    seed(config_path, synthetic_pdf)
    assert classify(question, list_sources(load_config(config_path)))[0] == intent


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("¿Qué documentos tienes?", "meta:inventory"),
        ("¿De qué trata el ACME-100?", "meta:document"),
        ("¿Qué sabes hacer?", "meta:capabilities"),
    ],
)
def test_meta_answers_come_from_index_and_cite_literal_headings(
    config_path: Path,
    synthetic_pdf: Path,
    question: str,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed(config_path, synthetic_pdf)

    def no_model(*a: Any, **k: Any) -> Any:
        raise AssertionError("una pregunta meta no debe llamar a los modelos")

    monkeypatch.setattr(ask_module, "build_adapters", no_model)
    evs = stream(config_path, question)
    done = evs[-1][1]
    assert done["ok"] is True and done["reason"] == reason
    assert "".join(d["text"] for k, d in evs if k == "token") == done["answer"]
    assert "ACME-100" in done["answer"]
    for c in done["citations"]:
        assert c["quote"] and c["quote"] in c["fragment"]
        assert c["quote"] in done["answer"] or reason == "meta:capabilities"


def test_empty_index_gives_useful_refusal(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fakes(monkeypatch, FakeLLM())
    evs = stream(config_path, "¿A qué voltaje opera?")
    assert evs[-1][1]["reason"] == "empty_index" and "Fuentes" in evs[-1][1]["answer"]
    assert (
        "Todavía no hay fuentes" in stream(config_path, "¿Qué documentos tienes?")[-1][1]["answer"]
    )


def test_ask_non_streaming_still_returns_same_contract(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)
    use_fakes(monkeypatch, FakeLLM())
    with TestClient(create_app(config_path)) as client:
        body = client.post("/ask", json={"question": "¿Cuánto cuesta?"}).json()
    assert body["ok"] is False and body["reason"] == "llm_unanswerable"
    assert body["suggestions"][0]["doc_id"].startswith("pdf-")


def test_sources_list_delete_reindex(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seeded = seed(config_path, synthetic_pdf)
    monkeypatch.setattr(
        "doc_assistant.ingest.build_adapters",
        lambda cfg, fake=False: (FakeEmbedder(), FakeReranker(), FakeLLM()),
    )
    cfg = load_config(config_path)
    with TestClient(create_app(config_path)) as client:
        [src] = client.get("/sources").json()
        assert src["id"] == seeded["doc_id"] and src["kind"] == "pdf" and src["status"] == "indexed"
        assert src["n_pages"] == 1 and src["n_chunks"] == seeded["n_chunks"]
        assert src["title"] == "Manual del Robot ACME-100" and src["added_at"]
        assert [s["section"] for s in src["sections"]] == ["1", "2", "2.1"]
        again = client.post(f"/sources/{src['id']}/reindex").json()
        assert sorted(again["chunk_ids"]) == sorted(seeded["chunk_ids"])
        assert client.post("/sources/nope/reindex").status_code == 404
        assert client.delete(f"/sources/{src['id']}").status_code == 204
        assert client.get("/sources").json() == []
        assert client.delete(f"/sources/{src['id']}").status_code == 404
    assert not (cfg.data_dir / "documents/ACME-100.pdf").exists()
    assert [p.name.endswith("_ACME-100.pdf") for p in (cfg.data_dir / "_removed").iterdir()] == [
        True
    ]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def fake_llama() -> Any:
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/fake_llama.py"), "--port", str(port)]
    )
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(5)


def test_http_llm_chat_stream_against_fake_llama(fake_llama: str) -> None:
    llm = HttpLLM(f"{fake_llama}/v1/chat/completions", "m", 5)
    text = "".join(llm.chat_stream([{"role": "user", "content": "x"}], {"type": "object"}))
    assert json.loads(text) == {"answerable": False, "answer": None, "citations": []}


def test_stream_end_to_end_over_http_adapters(
    config_path: Path, synthetic_pdf: Path, fake_llama: str
) -> None:
    """Pipeline real (adaptadores HTTP, SSE de llama-server simulado), sin fakes en proceso."""
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for key in ("llm", "embeddings", "reranker"):
        cfg[key]["base_url"] = fake_llama
    cfg["embeddings"]["dim"] = 1024
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    save_and_ingest_pdf(config_path, synthetic_pdf.read_bytes(), "manual.pdf")
    evs = stream(config_path, "¿A qué voltaje opera el robot?")
    kinds = [k for k, _ in evs]
    assert kinds[0] == "step" and kinds[-2:] == ["refusal", "done"]
    assert evs[-1][1]["reason"] == "llm_unanswerable"
    assert evs[-1][1]["answer"] == ask_module.NO_INFO


def test_scope_sentence_is_verbatim_first_sentence() -> None:
    from doc_assistant.meta import _scope_sentence

    body = "Este documento define la instalación. Incluye cableado."
    chunk = {"heading": "1. Alcance", "body": body, "text": f"[d · t · 1. Alcance] {body}"}
    other = {"heading": "2. Cableado", "body": "x.", "text": "x."}
    assert _scope_sentence([other, chunk]) == (chunk, "Este documento define la instalación.")
    assert _scope_sentence([other]) is None
