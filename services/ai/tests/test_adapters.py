"""Protocolos Embedder/Reranker/LLM y fakes; config swap."""

from __future__ import annotations

from pathlib import Path

import yaml
from doubles import FakeEmbedder, FakeLLM, FakeReranker

from doc_assistant.bootstrap import build_adapters
from doc_assistant.config import load_config
from doc_assistant.infra.models.http import HttpEmbedder


def test_fake_embedder_dim() -> None:
    e = FakeEmbedder(dim=8)
    vecs = e.embed(["hola", "mundo"])
    assert len(vecs) == 2
    assert all(len(v) == 8 for v in vecs)


def test_fake_reranker_preserves_order_scores() -> None:
    r = FakeReranker()
    scores = r.rerank("q", ["a", "b", "c"])
    assert len(scores) == 3
    assert scores[0][0] == 0


def test_fake_llm_json_schema_shape() -> None:
    llm = FakeLLM(
        response={
            "answerable": True,
            "answer": "24 V",
            "citations": [{"chunk_id": "abc", "quote": "24 V"}],
        }
    )
    out = llm.chat([{"role": "user", "content": "x"}], schema={"type": "object"})
    assert out["answerable"] is True
    assert out["citations"][0]["chunk_id"] == "abc"


def test_config_swap_changes_ports(tmp_path: Path) -> None:
    cfg_a = {
        "db": str(tmp_path / "a.db"),
        "docs": str(tmp_path / "docs"),
        "data_dir": str(tmp_path / "data"),
        "llm": {
            "base_url": "http://127.0.0.1:8081",
            "endpoint": "/v1/chat/completions",
            "model": "m1",
            "timeout_s": 90,
        },
        "embeddings": {
            "base_url": "http://127.0.0.1:8082",
            "endpoint": "/v1/embeddings",
            "model": "e1",
            "timeout_s": 90,
            "dim": 8,
        },
        "reranker": {
            "base_url": "http://127.0.0.1:8083",
            "endpoint": "/v1/rerank",
            "model": "r1",
            "timeout_s": 90,
        },
        "top_k": 5,
    }
    cfg_b = dict(cfg_a)
    cfg_b["embeddings"] = dict(cfg_a["embeddings"])
    cfg_b["embeddings"]["base_url"] = "http://127.0.0.1:9082"
    cfg_b["embeddings"]["model"] = "e2"
    cfg_b["llm"] = dict(cfg_a["llm"])
    cfg_b["llm"]["model"] = "m2"

    pa = tmp_path / "a.yaml"
    pb = tmp_path / "b.yaml"
    pa.write_text(yaml.dump(cfg_a), encoding="utf-8")
    pb.write_text(yaml.dump(cfg_b), encoding="utf-8")

    a = load_config(pa)
    b = load_config(pb)
    assert a.embeddings.base_url != b.embeddings.base_url
    assert a.embeddings.model != b.embeddings.model
    assert a.llm.model != b.llm.model

    emb_a, _, llm_a = build_adapters(a)
    emb_b, _, llm_b = build_adapters(b)
    assert isinstance(emb_a, HttpEmbedder)
    assert emb_a.url != emb_b.url
    assert llm_a.model != llm_b.model
