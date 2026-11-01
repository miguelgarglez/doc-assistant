from doubles import FakeEmbedder, FakeLLM, FakeReranker


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
