"""Pipeline ask con fakes: verificado, rechazo, cita falsa rechazada."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from doc_assistant.ask import ask, ask_events
from doc_assistant.chunking import chunk_pdf
from doc_assistant.infra.history.sqlite import HistoryStore
from doc_assistant.infra.storage.chunks import ChunkStore
from doc_assistant.model_fakes import FakeEmbedder, FakeLLM, FakeReranker


def _seed(tmp_path: Path, synthetic_pdf: Path, embedder: FakeEmbedder) -> ChunkStore:
    store = ChunkStore(tmp_path / "ask.db", dim=embedder.dim)
    chunks = chunk_pdf(synthetic_pdf, doc="manual")
    embs = embedder.embed([c["text"] for c in chunks])
    store.upsert(chunks, embs)
    return store


def test_ask_verified_answer(
    tmp_path: Path, synthetic_pdf: Path, config_path: Path, fake_embedder: FakeEmbedder
) -> None:
    store = _seed(tmp_path, synthetic_pdf, fake_embedder)
    # Point config db at seeded store
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["db"] = str(store.path)
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")

    chunk = store.get_by_section("1")
    quote = "24 V"
    assert quote in chunk["body"]

    llm = FakeLLM(
        response={
            "answerable": True,
            "answer": "El robot debe operar a 24 V.",
            "citations": [{"chunk_id": chunk["chunk_id"], "quote": quote}],
        }
    )
    result = ask(
        config_path,
        "¿A qué voltaje opera?",
        embedder=fake_embedder,
        reranker=FakeReranker(),
        llm=llm,
    )
    assert result["ok"] is True
    assert "24 V" in result["answer"]
    assert result["citations"]
    assert "latencies" in result


def test_trace_hashes_config_used_even_if_file_changes(
    tmp_path: Path, synthetic_pdf: Path, config_path: Path, fake_embedder: FakeEmbedder, monkeypatch
) -> None:
    import importlib

    import yaml

    ask_module = importlib.import_module("doc_assistant.ask")
    store = _seed(tmp_path, synthetic_pdf, fake_embedder)
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["db"] = str(store.path)
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    expected = hashlib.sha256(config_path.read_bytes()).hexdigest()
    load_config = ask_module.load_config

    def load_then_change(path):
        loaded = load_config(path)
        config_path.write_text("changed: true\n", encoding="utf-8")
        return loaded

    monkeypatch.setattr(ask_module, "load_config", load_then_change)
    trace: dict = {}
    ask(
        config_path,
        "¿A qué voltaje opera?",
        embedder=fake_embedder,
        reranker=FakeReranker(),
        llm=FakeLLM(response={"answerable": False, "answer": None, "citations": []}),
        trace=trace,
    )
    assert trace["versions"]["config_sha256"] == expected


def test_private_trace_captures_scores_without_changing_events(
    tmp_path: Path, synthetic_pdf: Path, config_path: Path, fake_embedder: FakeEmbedder
) -> None:
    import yaml

    store = _seed(tmp_path, synthetic_pdf, fake_embedder)
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["db"] = str(store.path)
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")
    chunk = store.get_by_section("1")
    llm = FakeLLM(
        response={
            "answerable": True,
            "answer": "El robot debe operar a 24 V.",
            "citations": [{"chunk_id": chunk["chunk_id"], "quote": "24 V"}],
        }
    )
    trace: dict = {}
    events = list(
        ask_events(
            config_path,
            "¿A qué voltaje opera?",
            embedder=fake_embedder,
            reranker=FakeReranker(),
            llm=llm,
            trace=trace,
        )
    )
    assert len(trace["versions"]["config_sha256"]) == 64
    assert len(trace["versions"]["answer_prompts_sha256"]) == 64
    assert len(trace["versions"]["chunk_index_sha256"]) == 64
    assert trace["versions"]["index_schema_version"] == 2
    assert set(trace["versions"]["models_configured"]) == {"llm", "embeddings", "reranker", "ocr"}
    selected = [c for c in trace["candidates"] if c["selected"]]
    assert selected and all(c["rerank_score"] is not None for c in selected)
    assert sorted(c["rerank_position"] for c in selected) == list(range(len(selected)))
    ranked = sorted(trace["candidates"], key=lambda c: c["rerank_position"])
    assert [c["rerank_score"] for c in ranked] == sorted(
        (c["rerank_score"] for c in ranked), reverse=True
    )
    candidate = next(c for c in trace["candidates"] if c["chunk_id"] == chunk["chunk_id"])
    assert candidate["text_sha256"] == hashlib.sha256(chunk["text"].encode()).hexdigest()
    assert any(c["vector_score"] is not None for c in trace["candidates"])
    assert trace["kind"] == "answer"
    assert trace["verification"]["ok"] is True
    assert trace["verification"]["details"]["citation_modes"] == ["literal"]
    assert trace["verification"]["citations"][0]["quote"] == "24 V"
    assert all("candidates" not in data for _, data in events)
    assert events[-1][1]["ok"] is True
    history = HistoryStore(tmp_path / "history.db")
    history.record("request", "conversation", trace["started_at"], trace)
    assert history.get("conversation", "request") == trace
    assert history.add_feedback(
        "feedback", "conversation", "request", trace["finished_at"], "otro", None
    )
    events[-1][1]["citations"][0]["quote"] = "modificada por el consumidor"
    assert trace["result"]["citations"][0]["quote"] == "24 V"
    events[-1][1]["raw"]["citations"][0]["quote"] = "otra modificación"
    assert trace["verification"]["citations"][0]["quote"] == "24 V"
    store.db.execute("UPDATE chunks SET title = ? WHERE chunk_id = ?", ("nuevo", chunk["chunk_id"]))
    store.db.commit()
    changed: dict = {}
    list(
        ask_events(
            config_path,
            "¿A qué voltaje opera?",
            embedder=fake_embedder,
            reranker=FakeReranker(),
            llm=llm,
            trace=changed,
        )
    )
    assert changed["versions"]["chunk_index_sha256"] != trace["versions"]["chunk_index_sha256"]


def test_ask_llm_rejects(
    tmp_path: Path, synthetic_pdf: Path, config_path: Path, fake_embedder: FakeEmbedder
) -> None:
    store = _seed(tmp_path, synthetic_pdf, fake_embedder)
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["db"] = str(store.path)
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")

    llm = FakeLLM(response={"answerable": False, "answer": None, "citations": []})
    result = ask(
        config_path,
        "¿Color favorito del robot?",
        embedder=fake_embedder,
        reranker=FakeReranker(),
        llm=llm,
    )
    assert result["ok"] is False
    assert "No dispongo" in result["answer"]
    assert result["reason"] in ("llm_unanswerable", "unanswerable")


def test_ask_false_citation_rejected(
    tmp_path: Path, synthetic_pdf: Path, config_path: Path, fake_embedder: FakeEmbedder
) -> None:
    store = _seed(tmp_path, synthetic_pdf, fake_embedder)
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["db"] = str(store.path)
    config_path.write_text(yaml.dump(cfg), encoding="utf-8")

    chunk = store.get_by_section("1")
    llm = FakeLLM(
        response={
            "answerable": True,
            "answer": "Opera a 48 V.",
            "citations": [
                {"chunk_id": chunk["chunk_id"], "quote": "texto inventado que no existe"}
            ],
        }
    )
    trace: dict = {}
    events = list(
        ask_events(
            config_path,
            "¿Voltaje?",
            embedder=fake_embedder,
            reranker=FakeReranker(),
            llm=llm,
            trace=trace,
        )
    )
    result = events[-1][1]
    assert trace["verification"]["ok"] is False
    assert trace["verification"]["details"]["citation_modes"] == []
    assert result["ok"] is False
    assert "No dispongo" in result["answer"]
    assert result["reason"].startswith("verify") or "quote" in result["reason"]


def test_answerable_without_answer_is_refused(
    config_path: Path, fake_embedder: FakeEmbedder
) -> None:
    result = ask(
        config_path,
        "¿Qué dice el documento?",
        embedder=fake_embedder,
        reranker=FakeReranker(),
        llm=FakeLLM(response={"answerable": True, "answer": None, "citations": []}),
    )
    assert result["ok"] is False
    assert result["citations"] == []


def test_trace_marks_completion_and_interruption(config_path: Path) -> None:
    completed: dict = {}
    events = list(ask_events(config_path, "", trace=completed))
    assert completed["status"] == "completed"
    assert completed["kind"] == "refusal"
    assert completed["result"] == events[-1][1]
    assert completed["trace_schema_version"] == 1
    assert completed["started_at"] <= completed["finished_at"]
    interrupted: dict = {}
    stream = ask_events(config_path, "Una pregunta", trace=interrupted)
    next(stream)
    stream.close()
    assert interrupted["status"] == "interrupted"
    assert interrupted["kind"] == "error"
    assert interrupted["steps"]
    assert "elapsed_s" in interrupted


def test_non_streaming_ask_can_collect_trace(config_path: Path) -> None:
    trace: dict = {}
    result = ask(config_path, "", trace=trace)
    assert result["reason"] == "pregunta_vacia"
    assert trace["result"] == result
    assert trace["status"] == "completed"


def test_trace_marks_pipeline_error(config_path: Path, monkeypatch) -> None:
    import pytest

    def fail(*args, **kwargs):
        raise RuntimeError("failure")
        yield

    monkeypatch.setattr("doc_assistant.ask._ask_events", fail)
    trace: dict = {}
    with pytest.raises(RuntimeError, match="failure"):
        list(ask_events(config_path, "pregunta", trace=trace))
    assert trace["status"] == "error"
    assert trace["kind"] == "error"
    assert trace["error_code"] == "internal_error"
    assert trace["started_at"] <= trace["finished_at"]
    assert "elapsed_s" in trace


def test_trace_marks_pipeline_without_result_as_error(config_path: Path, monkeypatch) -> None:
    from doc_assistant import ask as ask_module

    def incomplete_events(*args, **kwargs):
        yield "token", {"text": "incompleto"}

    monkeypatch.setattr(ask_module, "_ask_events", incomplete_events)
    trace: dict = {}
    with pytest.raises(RuntimeError, match="without a result"):
        list(ask_module.ask_events(config_path, "pregunta", trace=trace))
    assert trace["status"] == "error"
    assert trace["kind"] == "error"
    assert trace["error_code"] == "internal_error"


def test_trace_distinguishes_clarification(config_path: Path, monkeypatch) -> None:
    def clarify(*args, **kwargs):
        yield "result", {"ok": False, "clarification": {"candidates": ["A", "B"]}}

    monkeypatch.setattr("doc_assistant.ask._ask_events", clarify)
    trace: dict = {}
    list(ask_events(config_path, "pregunta", trace=trace))
    assert trace["kind"] == "clarification"


def test_invoice_trace_survives_planner_failure(config_path, fake_embedder, monkeypatch):
    import importlib

    import pytest

    from doc_assistant.application.ports.models import AdapterBusy

    module = importlib.import_module("doc_assistant.ask")
    monkeypatch.setattr(module, "list_sources", lambda cfg: [{"kind": "invoice"}])
    monkeypatch.setattr(module, "classify", lambda question, sources: ("rag", []))

    def fail(config_path, question, *, llm, trace):
        trace["plan_prompt_sha256"] = "planner-hash"
        raise AdapterBusy("busy")

    monkeypatch.setattr(module, "ask_invoices", fail)
    trace = {}
    with pytest.raises(AdapterBusy):
        list(
            ask_events(
                config_path,
                "factura",
                embedder=fake_embedder,
                reranker=FakeReranker(),
                llm=FakeLLM(response={}),
                trace=trace,
            )
        )
    assert trace["invoice"]["plan_prompt_sha256"] == "planner-hash"
    assert trace["status"] == "error"
