"""Overview ("meta") questions answered from index metadata, without the LLM.

The grounding guarantee holds by construction: every sentence is a template
filled with values read from the index (names, titles, section headings,
counts), and every listed heading is cited with a quote that appears verbatim
in its chunk. Routing is a small rule set: a misroute can only yield an
inventory of real sources, never an invented fact.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from doc_assistant.config import AppConfig
from doc_assistant.domain.answers.answer_markup import (
    AnswerBuilder,
    md_escape,
    section_label,
    split_heading,
)
from doc_assistant.invoice_fields import display_value
from doc_assistant.store import ChunkStore


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", " ", text).strip()


_CAPABILITIES = re.compile(
    r"\b(?:que|en que|como)\b.*\b(?:sabes|puedes|podrias)\s+(?:\w+\s+)?"
    r"(?:hacer|ayudar\w*|responder|contestar)\b"
    r"|\bque\s+(?:tipo\s+de\s+)?preguntas\s+(?:puedo|se\s+pueden|respondes|sabes)\b"
    r"|\bpara\s+que\s+sirves\b|\bque\s+eres\b|\bcomo\s+funcionas\b"
)
_INVENTORY = re.compile(
    r"\b(?:que|cuales|cuantos|cuantas)\s+(?:son\s+(?:los|las)\s+)?"
    r"(?:documentos|fuentes|manuales|archivos|ficheros|pdfs?|facturas)\s+"
    r"(?:tienes|hay|conoces|manejas|tengo|estan|has)\b"
    r"|\bresum\w*\s+(?:lo\s+que\s+(?:hay|tienes|sabes)|todo|los\s+documentos|las\s+fuentes)\b"
    r"|\bque\s+(?:hay|tienes)\s+(?:indexad\w*|cargad\w*|subid\w*)\b"
    r"|\bque\s+informacion\s+tienes\b|\b(?:lista|listado)\s+de\s+(?:documentos|fuentes)\b"
)
_DOCUMENT = re.compile(
    r"\bde\s+que\s+(?:trata|va|habla)\b|\bque\s+(?:contiene|cubre|incluye|tiene)\b"
    r"|\bresum\w*\b|\bque\s+sabes\s+(?:de|del|sobre)\b|\bindice\s+(?:de|del)\b"
)


def match_documents(question: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = f" {normalize(question)} "
    hits = []
    for s in sources:
        if s["kind"] != "pdf" or not s["n_chunks"]:
            continue
        names = {normalize(s["name"])}
        if s["title"] and len(normalize(s["title"]).split()) >= 2:
            names.add(normalize(s["title"]))
        if any(n and f" {n} " in q for n in names):
            hits.append(s)
    return hits


def classify(question: str, sources: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Return (intent, matched documents). intent: capabilities|inventory|document|rag."""
    q = normalize(question)
    if _CAPABILITIES.search(q):
        return "capabilities", []
    if _INVENTORY.search(q):
        return "inventory", []
    if _DOCUMENT.search(q):
        docs = match_documents(question, sources)
        if docs:
            return "document", docs
    return "rag", []


def _citation(chunk: dict[str, Any], quote: str | None = None) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "quote": quote or chunk["heading"],
        "doc": chunk["display_doc"],
        "doc_id": chunk["doc"],
        "section": chunk["section"],
        "pages": chunk["pages"],
        "fragment": chunk["text"],
    }


_SCOPE = re.compile(
    r"\b(?:alcance|objeto|objetivo|introduccion|resumen|descripcion(?: general)?|"
    r"vision general|scope|overview|introduction|purpose)\b"
)


def _scope_sentence(chunks: list[dict[str, Any]]) -> tuple[dict[str, Any], str] | None:
    """First sentence, verbatim, of a scope-like section: extractive, never paraphrased."""
    for c in chunks:
        if _SCOPE.search(normalize(c["heading"])):
            body = c.get("body") or ""
            sentence = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0].strip()
            if sentence and sentence in c["text"]:
                return c, sentence
    return None


def _all_chunks(cfg: AppConfig) -> dict[str, list[dict[str, Any]]]:
    """Chunks with a verbatim heading, per document, in section order."""
    from doc_assistant.sources import _section_key

    store = ChunkStore(cfg.db, cfg.embeddings.dim or 8)
    try:
        rows = [store._row(r) for r in store.db.execute("SELECT * FROM chunks")]
    finally:
        store.db.close()
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for c in rows:
        if c.get("heading") and c["heading"] in c["text"]:
            by_doc.setdefault(c["doc"], []).append(c)
    for chunks in by_doc.values():
        chunks.sort(key=lambda c: _section_key(c["section"]))
    return by_doc


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _pages(n: int) -> str:
    return _count(n, "página", "páginas")


def _doc_cite(s: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """One citation that stands for the whole document: its title on the first page."""
    if not chunks:
        return None
    first = chunks[0]
    title = s["title"]
    return _citation(first, title if title and title in first["text"] else first["heading"])


def _doc_text(s: dict[str, Any]) -> str:
    title = f": {md_escape(s['title'])}" if s["title"] else ""
    return f"**{md_escape(s['name'])}**{title}"


def _doc_item(s: dict[str, Any]) -> str:
    n = len(s["sections"])
    return f"{_doc_text(s)}. {_pages(s['n_pages'])} y {_count(n, 'apartado', 'apartados')}."


_FIELD = re.compile(r"(\w+): ([^;]+)")


def _invoice_item(s: dict[str, Any], header: dict[str, Any] | None) -> str:
    fields = dict(_FIELD.findall((header or {}).get("body") or ""))
    parts = [fields.get("emisor"), fields.get("fecha_emision")]
    if fields.get("importe_total"):
        parts.append(f"total {display_value('importe_total', fields['importe_total'])}")
    detail = ", ".join(md_escape(p.strip()) for p in parts if p)
    review = " (marcada para revisar)" if s["status"] == "review" else ""
    return f"**{md_escape(s['name'])}**" + (f": {detail}" if detail else "") + review


def inventory_scope(question: str) -> str:
    """Which sources the question asks about: "pdf", "invoice" or "all"."""
    q = normalize(question)
    pdf = re.search(r"\b(?:documentos|manuales|pdfs?)\b", q)
    invoice = re.search(r"\bfacturas?\b", q)
    if invoice and not pdf:
        return "invoice"
    if pdf and not invoice:
        return "pdf"
    return "all"


def _empty() -> dict[str, Any]:
    return _result(
        "meta:inventory",
        "Todavía no hay fuentes indexadas. Sube PDFs técnicos o imágenes de facturas "
        "en Fuentes y podré responder sobre ellos citando documento, sección y página.",
        [],
        [],
    )


def answer_meta(
    cfg: AppConfig,
    intent: str,
    docs: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    question: str = "",
) -> dict[str, Any]:
    pdfs = [s for s in sources if s["kind"] == "pdf" and s["n_chunks"]]
    invoices = [s for s in sources if s["kind"] == "invoice"]
    chunks = _all_chunks(cfg)
    out = AnswerBuilder()

    if intent == "document":
        for s in docs:
            doc_chunks = chunks.get(s["id"], [])
            out.paragraph(_doc_text(s) + ".", [c for c in [_doc_cite(s, doc_chunks)] if c])
            scope = _scope_sentence(doc_chunks)
            if scope:
                chunk, sentence = scope
                _, title = split_heading(chunk["heading"])
                out.paragraph(
                    f"Según «{md_escape(title)}»: «{md_escape(sentence)}»",
                    [_citation(chunk, sentence)],
                )
            out.paragraph(
                f"{_pages(s['n_pages'])} y "
                f"{_count(len(doc_chunks), 'apartado indexado', 'apartados indexados')}:"
            )
            for c in doc_chunks:
                pages = ", ".join(str(p) for p in c["pages"])
                label = section_label(c["heading"])
                out.bullet(f"{label} (p. {pages})", [_citation(c)])
        out.paragraph(
            "No redacto resúmenes: solo muestro frases literales y el índice de apartados. "
            "Pregúntame por cualquiera de ellos y te respondo con la cita exacta."
        )
        return _finish("meta:document", out)

    if not pdfs and not invoices:
        return _empty()

    if intent == "capabilities":
        out.paragraph(
            "Respondo preguntas sobre las fuentes indexadas y cito siempre documento, "
            "sección, página y el fragmento literal. Si algo no está en las fuentes, "
            "te lo digo en vez de inventarlo."
        )
        out.paragraph("Puedo ayudarte con:")
        if pdfs:
            out.bullet(
                f"Datos concretos de {_count(len(pdfs), 'documento técnico', 'documentos técnicos')}, con la cita exacta."
            )
            out.bullet(
                f"El índice de apartados de un documento («¿de qué trata {md_escape('<documento>')}?»)."
            )
        if invoices:
            out.bullet(
                f"Campos de {_count(len(invoices), 'factura', 'facturas')} "
                "(número, fechas, emisor, importes, IVA)."
            )
        out.bullet("Qué fuentes hay («¿qué documentos tienes?»).")
        examples: list[tuple[str, dict[str, Any] | None]] = []
        for s in pdfs[:3]:
            doc_chunks = chunks.get(s["id"], [])
            if doc_chunks:
                c = doc_chunks[min(1, len(doc_chunks) - 1)]
                _, title = split_heading(c["heading"])
                examples.append(
                    (f"«¿Qué dice {md_escape(s['name'])} sobre {md_escape(title)}?»", _citation(c))
                )
        if invoices:
            examples.append(
                (
                    f"«¿Cuál es el importe total de la factura {md_escape(invoices[0]['name'])}?»",
                    None,
                )
            )
        if examples:
            out.paragraph("Ejemplos con las fuentes actuales:")
            for text, cite in examples:
                out.bullet(text, [cite] if cite else None)
        return _finish("meta:capabilities", out)

    kinds = inventory_scope(question)
    show_pdfs = pdfs if kinds in ("pdf", "all") else []
    show_invoices = invoices if kinds in ("invoice", "all") else []
    if not show_pdfs and not show_invoices:
        what = "documentos" if kinds == "pdf" else "facturas"
        out.paragraph(
            f"Todavía no hay {what} indexados. Súbelos en Fuentes y podré responder sobre ellos."
        )
        return _finish("meta:inventory", out)

    summary = []
    if show_pdfs:
        summary.append(_count(len(show_pdfs), "documento", "documentos"))
    if show_invoices:
        summary.append(_count(len(show_invoices), "factura", "facturas"))
    out.paragraph(f"Hay {' y '.join(summary)}:")
    if show_pdfs:
        if kinds == "all":
            out.paragraph("**Documentos**")
        for s in show_pdfs:
            cite = _doc_cite(s, chunks.get(s["id"], []))
            out.bullet(_doc_item(s), [cite] if cite else None)
    if show_invoices:
        if kinds == "all":
            out.paragraph("**Facturas**")
        for s in show_invoices:
            doc_chunks = chunks.get(s["id"], [])
            header = next((c for c in doc_chunks if c["section"] == "cabecera"), None)
            cite = _citation(header, f"Factura {s['name']}") if header else None
            out.bullet(_invoice_item(s, header), [cite] if cite else None)
    if kinds == "pdf" and invoices:
        out.paragraph(
            f"También hay {_count(len(invoices), 'factura indexada', 'facturas indexadas')}. "
            "Pregunta «¿qué facturas tengo?» para verlas."
        )
    elif kinds == "invoice" and pdfs:
        out.paragraph(
            f"También hay {_count(len(pdfs), 'documento indexado', 'documentos indexados')}. "
            "Pregunta «¿qué documentos tienes?» para verlos."
        )
    out.paragraph("Pregúntame por cualquiera y te respondo con la cita exacta.")
    return _finish("meta:inventory", out)


def _finish(reason: str, out: AnswerBuilder) -> dict[str, Any]:
    answer, citations, segments = out.build()
    return _result(reason, answer, citations, segments)


def _result(
    reason: str, answer: str, citations: list[dict[str, Any]], segments: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "ok": True,
        "answer": answer,
        "citations": citations,
        "segments": segments,
        "inline": "template",
        "reason": reason,
        "suggestions": [],
        "latencies": {},
        "raw": None,
    }


def suggestions_from(chunks: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in chunks:
        if len(out) >= limit:
            break
        if any(o["doc_id"] == c["doc"] and o["section"] == c["section"] for o in out):
            continue
        out.append(
            {
                "doc": c.get("display_doc") or c["doc"],
                "doc_id": c["doc"],
                "section": c["section"],
                "heading": c.get("heading"),
                "pages": c.get("pages") or [],
            }
        )
    return out


def related_follow_ups(
    suggestions: list[dict[str, Any]], cited: list[dict[str, Any]], limit: int = 2
) -> list[dict[str, str]]:
    """Nearby sections the answer did not cite, as questions the index can answer."""
    seen = {(c.get("doc_id"), c.get("section")) for c in cited}
    out: list[dict[str, str]] = []
    for item in suggestions:
        if (item["doc_id"], item["section"]) in seen:
            continue
        topic = item.get("heading") or f"la sección {item['section']}"
        out.append(
            {
                "label": f"{item['doc']} · {topic}",
                "question": f"¿Qué dice {item['doc']} sobre {topic}?",
            }
        )
        if len(out) == limit:
            break
    return out
