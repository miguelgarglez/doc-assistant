"""SSE /ask/stream, preguntas meta y catálogo de fuentes."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from doc_assistant import ask as ask_module
from doc_assistant import ask_stream as stream_module
from doc_assistant.api import create_app
from doc_assistant.ask_stream import ask_stream_events
from doc_assistant.config import load_config
from doc_assistant.ingest import save_and_ingest_pdf
from doc_assistant.meta import classify
from doc_assistant.model_fakes import FakeEmbedder, FakeLLM, FakeReranker
from doc_assistant.model_http import HttpLLM
from doc_assistant.model_ports import AdapterBusy, AdapterError
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
    kinds = [k for k, _ in evs if k != "blocks"]
    assert kinds[-2:] == ["citations", "done"]
    assert "".join(d["text"] for k, d in evs if k == "token") == answer
    steps = [(d["id"], d["status"]) for k, d in evs if k == "step"]
    for sid in ("route", "retrieve", "rerank", "generate", "verify"):
        assert (sid, "running") in steps and (sid, "done") in steps
    done = evs[-1][1]
    assert done["ok"] is True and done["answer"] == answer and done["reason"] == "verified"
    assert done["timings"]["total"] >= 0
    cited = {(c["doc_id"], c["section"]) for c in done["citations"]}
    for follow_up in done["follow_ups"]:
        assert follow_up["question"].startswith("¿Qué dice ")
    assert len(done["follow_ups"]) <= 2 and cited
    blocks = [d for k, d in evs if k == "blocks"]
    assert bool(blocks) == bool(done["follow_ups"])
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


def test_stream_busy_model_reports_retryable_error(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)

    class Busy(FakeLLM):
        def chat_stream(self, messages: Any, schema: Any) -> Any:
            raise AdapterBusy("HTTP 503 en http://localhost:8191")
            yield  # pragma: no cover

    use_fakes(monkeypatch, Busy())
    evs = stream(config_path, "¿A qué voltaje opera el robot?")
    assert evs[-1] == (
        "error",
        {
            "code": "model_busy",
            "message": "El modelo está ocupado o no está disponible. Inténtalo de nuevo en unos segundos.",
        },
    )
    assert "done" not in [kind for kind, _ in evs]


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
        title = c["quote"].split(". ", 1)[-1]
        assert title in done["answer"] or reason == "meta:capabilities"


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


def test_stream_ambiguous_invoice_is_a_clarification_not_a_refusal(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from doc_assistant.chunking import chunk_invoice
    from doc_assistant.invoices import InvoiceDB

    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    store = ChunkStore(cfg.db, 8)
    try:
        for numero, total in (("F-1", "10.00"), ("F-2", "20.00")):
            record = {"numero": numero, "emisor": "Emisor Uno", "importe_total": total}
            db.upsert(record)
            chunks = chunk_invoice({"numero": numero, "total": total})
            store.replace_document(
                chunks[0]["doc"], chunks, FakeEmbedder().embed([c["text"] for c in chunks]), []
            )
    finally:
        db.con.close()
        store.db.close()
    use_fakes(monkeypatch, FakeLLM({"intent": "valor", "campos": ["importe_total"]}))
    evs = stream(config_path, "¿cuál es el importe total de la factura?")
    kinds = [k for k, _ in evs]
    assert kinds[-2:] == ["clarification", "done"] and "refusal" not in kinds
    event, done = evs[-2][1], evs[-1][1]
    assert event["reason"] == "invoice:aclaracion"
    assert [c["doc"] for c in event["clarification"]["candidates"]] == ["F-1", "F-2"]
    assert event["clarification"]["candidates"][0]["question"] == (
        "¿Cuál es el importe total de la factura F-1?"
    )
    assert done["ok"] is False and done["clarification"] == event["clarification"]
    assert done["suggestions"] == []

    with TestClient(create_app(config_path)) as client:
        plain = client.post(
            "/ask", json={"question": "¿cuál es el importe total de la factura?"}
        ).json()
    assert plain["clarification"] == event["clarification"] and "¿Te refieres" in plain["answer"]


def seed_invoice(config_path: Path, record: dict[str, str]) -> None:
    from doc_assistant.chunking import chunk_invoice
    from doc_assistant.invoices import InvoiceDB

    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    store = ChunkStore(cfg.db, 8)
    try:
        db.upsert(record)
        chunks = chunk_invoice({"numero": record["numero"], "total": record["importe_total"]})
        store.replace_document(
            chunks[0]["doc"], chunks, FakeEmbedder().embed([c["text"] for c in chunks]), []
        )
    finally:
        db.con.close()
        store.db.close()


def test_stream_invoice_answer_sends_blocks_after_citations_and_in_done(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_invoice(
        config_path,
        {
            "numero": "F-7",
            "emisor": "Emisor Uno",
            "cliente": "Cliente Dos",
            "fecha_emision": "2026-03-01",
            "fecha_vencimiento": "2026-04-01",
            "importe_total": "1706.60",
        },
    )
    use_fakes(
        monkeypatch,
        FakeLLM({"intent": "valor", "numero": "F-7", "campos": ["importe_total"]}),
    )
    evs = stream(config_path, "¿cuál es el importe total de la factura F-7?")
    kinds = [k for k, _ in evs]
    assert kinds[-3:] == ["citations", "blocks", "done"]
    blocks, done = evs[-2][1], evs[-1][1]
    assert blocks["blocks"][0]["type"] == "key_data"
    assert blocks["blocks"][0]["items"][0]["text"] == "1.706,60 €"
    assert blocks["blocks"] == done["blocks"] and blocks["follow_ups"] == done["follow_ups"]
    assert [f["label"] for f in done["follow_ups"]] == [
        "Fecha de vencimiento",
        "Fecha de emisión",
        "Emisor",
    ]


def test_stream_answer_without_blocks_sends_no_blocks_event(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_invoice(config_path, {"numero": "F-8", "importe_total": "10.00"})
    use_fakes(monkeypatch, FakeLLM({"intent": "contar"}))
    evs = stream(config_path, "¿cuántas facturas hay?")
    assert "blocks" not in [k for k, _ in evs]
    assert evs[-1][1]["blocks"] == [] and evs[-1][1]["follow_ups"] == []


def test_stream_survives_worker_thread_changes(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(config_path, synthetic_pdf)
    chunk = chunk_for(config_path, "1")
    use_fakes(
        monkeypatch,
        FakeLLM(
            {
                "answerable": True,
                "answer": "El robot opera a 24 V.",
                "citations": [{"chunk_id": chunk["chunk_id"], "quote": "24 V"}],
            }
        ),
    )
    iterator = ask_stream_events(config_path, "¿A qué voltaje opera el robot?")
    frames = []
    with ThreadPoolExecutor(max_workers=1) as a, ThreadPoolExecutor(max_workers=1) as b:
        for i in range(100):
            frame = (a if i % 2 == 0 else b).submit(next, iterator, None).result()
            if frame is None:
                break
            frames.append(frame)
    evs = events("".join(frames))
    assert evs[-1][0] == "done", evs[-1]
    assert evs[-1][1]["ok"] is True


def test_request_id_matches_stream_and_is_unique(config_path: Path) -> None:
    with TestClient(create_app(config_path)) as client:
        streamed = client.post("/ask/stream", json={"question": "¿Qué documentos tienes?"})
        plain = client.post("/ask", json={"question": "¿Qué documentos tienes?"})
    stream_id = streamed.headers["x-request-id"]
    assert str(uuid.UUID(stream_id)) == stream_id
    assert events(streamed.text)[-1][1]["request_id"] == stream_id
    assert str(uuid.UUID(plain.headers["x-request-id"])) == plain.headers["x-request-id"]
    assert plain.headers["x-request-id"] != stream_id


def test_stream_close_finalizes_optional_trace(config_path: Path) -> None:
    trace: dict = {}
    iterator = ask_stream_events(config_path, "¿Qué documentos tienes?", trace=trace)
    next(iterator)
    iterator.close()
    assert trace["status"] == "interrupted"
    assert trace["transport_status"] == "interrupted"
    assert trace["finished_at"] >= trace["started_at"]


def test_stream_can_interrupt_after_pipeline_result(config_path: Path) -> None:
    trace: dict = {}
    iterator = ask_stream_events(config_path, "", trace=trace)
    assert events(next(iterator))[0][0] == "refusal"
    iterator.close()
    assert trace["status"] == "completed"
    assert trace["transport_status"] == "interrupted"


def test_stream_close_after_done_keeps_transport_completed(config_path: Path) -> None:
    trace: dict = {}
    iterator = ask_stream_events(config_path, "", trace=trace)
    assert events(next(iterator))[0][0] == "refusal"
    assert events(next(iterator))[0][0] == "done"
    iterator.close()
    assert trace["status"] == "completed"
    assert trace["transport_status"] == "completed"


def test_stream_trace_records_translation_failure_without_exception_details(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def invalid_events(*args, **kwargs):
        yield "step", {"private": "secret"}

    monkeypatch.setattr(stream_module, "ask_events", invalid_events)
    trace: dict = {}
    frames = list(ask_stream_events(config_path, "pregunta", trace=trace))
    assert events("".join(frames))[-1][1]["code"] == "internal_error"
    assert trace["transport_status"] == "error"
    assert trace["transport_error_code"] == "internal_error"
    assert "secret" not in str(trace)


def test_stream_without_pipeline_result_ends_with_error(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def incomplete_events(*args, **kwargs):
        yield "token", {"text": "Respuesta incompleta"}

    monkeypatch.setattr(stream_module, "ask_events", incomplete_events)
    trace: dict = {}
    frames = list(ask_stream_events(config_path, "pregunta", trace=trace))
    parsed = events("".join(frames))
    assert [event[0] for event in parsed] == ["token", "error"]
    assert parsed[-1][1]["code"] == "internal_error"
    assert trace["transport_status"] == "error"
