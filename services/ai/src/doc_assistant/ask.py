"""Pipeline ask: vector∪BM25 → rerank → LLM json_schema → verifier."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from doc_assistant.adapters import (
    LLM,
    AdapterError,
    Embedder,
    Reranker,
    StreamingLLM,
    build_adapters,
)
from doc_assistant.config import load_config
from doc_assistant.invoices import ask_invoices
from doc_assistant.meta import answer_meta, classify, suggestions_from
from doc_assistant.partial_json import FieldStreamer
from doc_assistant.sources import list_sources
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
ROUTE_LABELS = {
    "capabilities": "Pregunta sobre lo que puedo hacer",
    "inventory": "Pregunta sobre las fuentes disponibles",
    "document": "Pregunta sobre el contenido de un documento",
    "rag": "Pregunta sobre el contenido de las fuentes",
}


def _union_candidates(vec: list[tuple[str, float]], bm: list[tuple[str, float]]) -> list[str]:
    seen: list[str] = []
    for cid, _ in vec + bm:
        if cid not in seen:
            seen.append(cid)
    return seen


Event = tuple[str, dict[str, Any]]


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _step(sid: str, status: str, label: str, **extra: Any) -> Event:
    return ("step", {"id": sid, "status": status, "label": label, **extra})


def _refusal(
    reason: str,
    latencies: dict[str, float],
    raw: Any = None,
    *,
    answer: str = NO_INFO,
    suggestions: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "ok": False,
        "answer": answer,
        "citations": [],
        "reason": reason,
        "suggestions": suggestions or [],
        "latencies": latencies,
        "raw": raw,
        **extra,
    }


def _chunked(text: str, size: int = 24) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def ask_events(
    config_path: str | Path,
    question: str,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
    stream: bool = False,
) -> Iterator[Event]:
    """Run the pipeline as a sequence of events; the last one is ("result", dict).

    `step` and `token` events are progress only. The result is the single source
    of truth: tokens are provisional until verification has passed.
    """
    q = (question or "").strip()
    if not q or len(q) > MAX_QUESTION_CHARS:
        why = "pregunta_vacia" if not q else "pregunta_demasiado_larga"
        msg = (
            "Escribe una pregunta."
            if not q
            else f"La pregunta es demasiado larga (máx. {MAX_QUESTION_CHARS} caracteres)."
        )
        yield ("result", _refusal(why, {}, answer=msg))
        return
    question = q
    cfg = load_config(config_path)
    latencies: dict[str, float] = {}

    t = time.perf_counter()
    yield _step("route", "running", "Analizando la pregunta")
    sources = list_sources(cfg)
    intent, matched = classify(question, sources)
    latencies["route"] = round(time.perf_counter() - t, 4)
    yield _step(
        "route",
        "done",
        ROUTE_LABELS[intent],
        data={"intent": intent},
        elapsed_s=latencies["route"],
    )
    if intent != "rag":
        t = time.perf_counter()
        yield _step("meta", "running", "Leyendo el índice de fuentes")
        result = answer_meta(cfg, intent, matched, sources)
        latencies["meta"] = round(time.perf_counter() - t, 4)
        yield _step(
            "meta",
            "done",
            f"{len(sources)} fuentes en el índice",
            data={"n": len(sources)},
            elapsed_s=latencies["meta"],
        )
        for piece in _chunked(result["answer"]):
            yield ("token", {"text": piece})
        result["latencies"] = latencies
        yield ("result", result)
        return

    if embedder is None or reranker is None or llm is None:
        e, r, l = build_adapters(cfg, fake=False)
        embedder = embedder or e
        reranker = reranker or r
        llm = llm or l

    if any(s["kind"] == "invoice" for s in sources):
        t = time.perf_counter()
        yield _step("invoices", "running", "Comprobando si es una consulta de facturas")
        invoice_result = ask_invoices(config_path, question, llm=llm)
        latencies["invoices"] = round(time.perf_counter() - t, 4)
        yield _step(
            "invoices",
            "done",
            "Consulta de facturas" if invoice_result else "No es una consulta de facturas",
            elapsed_s=latencies["invoices"],
        )
        if invoice_result is not None:
            invoice_result.setdefault("suggestions", [])
            invoice_result["latencies"] = latencies
            if invoice_result["ok"]:
                for piece in _chunked(invoice_result["answer"]):
                    yield ("token", {"text": piece})
            yield ("result", invoice_result)
            return

    if not any(s["n_chunks"] for s in sources):
        yield (
            "result",
            _refusal(
                "empty_index",
                latencies,
                answer="Todavía no hay documentos indexados. Sube PDFs en Fuentes y vuelve a preguntar.",
            ),
        )
        return

    dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
    store = ChunkStore(cfg.db, dim=dim)

    t0 = time.perf_counter()
    yield _step("retrieve", "running", "Buscando fragmentos relevantes")
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
    yield _step(
        "retrieve",
        "done",
        _count(len(ordered), "fragmento candidato", "fragmentos candidatos"),
        data={"n": len(ordered)},
        elapsed_s=round(time.perf_counter() - t0, 4),
    )

    t2 = time.perf_counter()
    yield _step("rerank", "running", "Reordenando por relevancia")
    if docs:
        ranked = reranker.rerank(question, docs)
        top_idx = [i for i, _ in ranked[: cfg.top_k]]
        top_chunks = [ordered[i] for i in top_idx if i < len(ordered)]
    else:
        top_chunks = []
    latencies["rerank"] = round(time.perf_counter() - t2, 4)
    yield _step(
        "rerank",
        "done",
        _count(len(top_chunks), "fragmento seleccionado", "fragmentos seleccionados"),
        data={
            "n": len(top_chunks),
            "top": [{"doc": c["display_doc"], "section": c["section"]} for c in top_chunks],
        },
        elapsed_s=latencies["rerank"],
    )
    suggestions = suggestions_from(top_chunks)

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
    messages = [
        {
            "role": "system",
            "content": EVIDENCE_FIRST_PROMPT
            if cfg.answer_mode == "evidence_first"
            else SYSTEM_PROMPT,
        },
        {"role": "user", "content": user_msg},
    ]
    schema = EVIDENCE_FIRST_SCHEMA if cfg.answer_mode == "evidence_first" else ANSWER_SCHEMA

    t3 = time.perf_counter()
    yield _step("generate", "running", "Redactando la respuesta con los fragmentos")
    if stream and isinstance(llm, StreamingLLM):
        streamer = FieldStreamer("answer")
        parts: list[str] = []
        for delta in llm.chat_stream(messages, schema):
            parts.append(delta)
            text = streamer.feed(delta)
            if text:
                yield ("token", {"text": text})
        try:
            raw = json.loads("".join(parts))
        except ValueError as e:
            raise AdapterError("Contenido LLM no es JSON válido (stream)") from e
        if not isinstance(raw, dict):
            raise AdapterError("Contenido LLM no es un objeto JSON (stream)")
    else:
        raw = llm.chat(messages, schema=schema)
    latencies["llm"] = round(time.perf_counter() - t3, 4)
    yield _step("generate", "done", "Respuesta redactada", elapsed_s=latencies["llm"])

    t4 = time.perf_counter()
    yield _step("verify", "running", "Verificando citas contra los fragmentos")
    if (
        not raw.get("answerable")
        or not isinstance(raw.get("answer"), str)
        or not raw["answer"].strip()
    ):
        latencies["verify"] = round(time.perf_counter() - t4, 4)
        yield _step("verify", "done", "Sin respaldo en las fuentes", elapsed_s=latencies["verify"])
        yield ("result", _refusal("llm_unanswerable", latencies, raw, suggestions=suggestions))
        return

    citations = raw.get("citations") or []
    answer = raw.get("answer")
    checked = verify(answer, citations, retrieved_text)
    latencies["verify"] = round(time.perf_counter() - t4, 4)

    if not checked.ok:
        yield _step(
            "verify", "done", "La respuesta no pasa la verificación", elapsed_s=latencies["verify"]
        )
        yield (
            "result",
            _refusal(
                f"verify:{checked.reason}",
                latencies,
                raw,
                suggestions=suggestions,
                verify_details=checked.details,
            ),
        )
        return
    yield _step(
        "verify",
        "done",
        _count(len(citations), "cita verificada", "citas verificadas"),
        data={"n_citations": len(citations)},
        elapsed_s=latencies["verify"],
    )

    enriched = []
    for cit in citations:
        meta = store.get(cit["chunk_id"]) or {}
        enriched.append(
            {
                "chunk_id": cit["chunk_id"],
                "quote": cit["quote"],
                "doc": meta.get("display_doc"),
                "doc_id": meta.get("doc"),
                "section": meta.get("section"),
                "pages": meta.get("pages"),
                "fragment": meta.get("text"),
            }
        )

    yield (
        "result",
        {
            "ok": True,
            "answer": answer,
            "citations": enriched,
            "reason": "verified",
            "suggestions": [],
            "latencies": latencies,
            "raw": raw,
        },
    )


def ask(
    config_path: str | Path,
    question: str,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for kind, data in ask_events(
        config_path, question, embedder=embedder, reranker=reranker, llm=llm
    ):
        if kind == "result":
            result = data
    return result


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
