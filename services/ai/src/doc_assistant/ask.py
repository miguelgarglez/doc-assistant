"""Pipeline ask: vector∪BM25 → rerank → LLM json_schema → verifier."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from doc_assistant.adapters import LLM, Embedder, Reranker, build_adapters
from doc_assistant.config import load_config
from doc_assistant.store import ChunkStore
from doc_assistant.verifier import verify

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "answer": {"type": ["string", "null"]},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["chunk_id", "quote"],
            },
        },
    },
    "required": ["answerable", "answer", "citations"],
}

SYSTEM_PROMPT = (
    "Responde SOLO con la información de los fragmentos proporcionados. "
    "Si la respuesta no está en los fragmentos, answerable=false, answer=null "
    "y citations=[]. Cada cita debe incluir chunk_id y una quote literal del fragmento."
)

# Evidence-first: the model copies the supporting sentences BEFORE deciding.
# JSON is generated in property order, so with "answerable" first the model
# commits to a refusal before it has looked for the sentence.
EVIDENCE_FIRST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "citations": ANSWER_SCHEMA["properties"]["citations"],
        "answer": {"type": ["string", "null"]},
        "answerable": {"type": "boolean"},
    },
    "required": ["citations", "answer", "answerable"],
}
EVIDENCE_FIRST_PROMPT = (
    "Responde SOLO con la información de los fragmentos. Primero busca y copia "
    "literalmente en citations las frases que responden (chunk_id + quote); la pregunta "
    "puede usar otras palabras que el manual. Después escribe answer usando solo esas "
    "frases. Si ninguna frase responde exactamente, citations=[], answer=null, "
    "answerable=false. Si la respuesta usa datos de dos fragmentos, cita los dos."
)

NO_INFO = "No dispongo de esa información en los documentos"
MAX_QUESTION_CHARS = 1000


def _union_candidates(vec: list[tuple[str, float]], bm: list[tuple[str, float]]) -> list[str]:
    seen: list[str] = []
    for cid, _ in vec + bm:
        if cid not in seen:
            seen.append(cid)
    return seen


def ask(
    config_path: str | Path,
    question: str,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    if not q or len(q) > MAX_QUESTION_CHARS:
        why = "pregunta_vacia" if not q else "pregunta_demasiado_larga"
        msg = (
            "Escribe una pregunta."
            if not q
            else f"La pregunta es demasiado larga (máx. {MAX_QUESTION_CHARS} caracteres)."
        )
        return {
            "ok": False,
            "answer": msg,
            "citations": [],
            "reason": why,
            "latencies": {},
            "raw": None,
        }
    question = q
    cfg = load_config(config_path)
    if embedder is None or reranker is None or llm is None:
        e, r, l = build_adapters(cfg, fake=False)
        embedder = embedder or e
        reranker = reranker or r
        llm = llm or l

    dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
    store = ChunkStore(cfg.db, dim=dim)
    latencies: dict[str, float] = {}

    t0 = time.perf_counter()
    q_emb = embedder.embed([question])[0]
    latencies["embed"] = round(time.perf_counter() - t0, 4)

    t1 = time.perf_counter()
    vec = store.vector_search(q_emb, k=10)
    bm = store.bm25(question, k=10)
    cand_ids = _union_candidates(vec, bm)
    latencies["search"] = round(time.perf_counter() - t1, 4)

    cand_chunks = store.get_many(cand_ids)
    ordered = [cand_chunks[i] for i in cand_ids if i in cand_chunks]
    docs = [c["text"] for c in ordered]

    t2 = time.perf_counter()
    if docs:
        ranked = reranker.rerank(question, docs)
        top_idx = [i for i, _ in ranked[: cfg.top_k]]
        top_chunks = [ordered[i] for i in top_idx if i < len(ordered)]
    else:
        top_chunks = []
    latencies["rerank"] = round(time.perf_counter() - t2, 4)

    context_blocks = []
    retrieved_text: dict[str, str] = {}
    for c in top_chunks:
        retrieved_text[c["chunk_id"]] = c["text"]
        pages = ",".join(str(p) for p in c.get("pages") or [])
        context_blocks.append(
            f"chunk_id={c['chunk_id']} doc={c['doc']} section={c['section']} "
            f"pages={pages}\n{c['text']}"
        )
    user_msg = f"Pregunta: {question}\n\nFragmentos:\n" + (
        "\n---\n".join(context_blocks) if context_blocks else "(ninguno)"
    )

    t3 = time.perf_counter()
    raw = llm.chat(
        [
            {
                "role": "system",
                "content": EVIDENCE_FIRST_PROMPT
                if cfg.answer_mode == "evidence_first"
                else SYSTEM_PROMPT,
            },
            {"role": "user", "content": user_msg},
        ],
        schema=EVIDENCE_FIRST_SCHEMA if cfg.answer_mode == "evidence_first" else ANSWER_SCHEMA,
    )
    latencies["llm"] = round(time.perf_counter() - t3, 4)

    t4 = time.perf_counter()
    if (
        not raw.get("answerable")
        or not isinstance(raw.get("answer"), str)
        or not raw["answer"].strip()
    ):
        latencies["verify"] = round(time.perf_counter() - t4, 4)
        return {
            "ok": False,
            "answer": NO_INFO,
            "citations": [],
            "reason": "llm_unanswerable",
            "latencies": latencies,
            "raw": raw,
        }

    citations = raw.get("citations") or []
    answer = raw.get("answer")
    result = verify(answer, citations, retrieved_text)
    latencies["verify"] = round(time.perf_counter() - t4, 4)

    if not result.ok:
        return {
            "ok": False,
            "answer": NO_INFO,
            "citations": [],
            "reason": f"verify:{result.reason}",
            "latencies": latencies,
            "raw": raw,
            "verify_details": result.details,
        }

    enriched = []
    for cit in citations:
        meta = store.get(cit["chunk_id"]) or {}
        enriched.append(
            {
                "chunk_id": cit["chunk_id"],
                "quote": cit["quote"],
                "doc": meta.get("doc"),
                "section": meta.get("section"),
                "pages": meta.get("pages"),
                "fragment": meta.get("text"),
            }
        )

    return {
        "ok": True,
        "answer": answer,
        "citations": enriched,
        "reason": "verified",
        "latencies": latencies,
        "raw": raw,
    }


def format_ask_text(result: dict[str, Any]) -> str:
    lines = [result["answer"]]
    if result.get("ok") and result.get("citations"):
        lines.append("")
        lines.append("Citas:")
        for c in result["citations"]:
            pages = c.get("pages") or []
            page_s = ",".join(str(p) for p in pages)
            lines.append(f"- [{c.get('doc')} §{c.get('section')} p.{page_s}] {c.get('quote')!r}")
            if c.get("fragment"):
                lines.append(f"  fragmento: {c['fragment'][:200]}")
    lat = result.get("latencies") or {}
    if lat:
        parts = ", ".join(f"{k}={v}s" for k, v in lat.items())
        lines.append(f"\nLatencias: {parts}")
    return "\n".join(lines)
