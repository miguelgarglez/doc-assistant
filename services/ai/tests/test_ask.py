"""Pipeline ask con fakes: verificado, rechazo, cita falsa rechazada."""

from __future__ import annotations

from pathlib import Path

from doc_assistant.adapters import FakeEmbedder, FakeLLM, FakeReranker
from doc_assistant.ask import ask
from doc_assistant.chunking import chunk_pdf
from doc_assistant.store import ChunkStore


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
    result = ask(
        config_path,
        "¿Voltaje?",
        embedder=fake_embedder,
        reranker=FakeReranker(),
        llm=llm,
    )
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
