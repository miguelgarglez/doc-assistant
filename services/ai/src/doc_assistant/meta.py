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


def _citation(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "quote": chunk["heading"],
        "doc": chunk["display_doc"],
        "doc_id": chunk["doc"],
        "section": chunk["section"],
        "pages": chunk["pages"],
        "fragment": chunk["text"],
    }


def _section_chunks(cfg: AppConfig, doc_id: str) -> list[dict[str, Any]]:
    store = ChunkStore(cfg.db, cfg.embeddings.dim or 8)
    try:
        rows = store.db.execute("SELECT * FROM chunks WHERE doc = ?", (doc_id,)).fetchall()
        chunks = [store._row(r) for r in rows]
    finally:
        store.db.close()
    from doc_assistant.sources import _section_key

    chunks = [c for c in chunks if c.get("heading") and c["heading"] in c["text"]]
    return sorted(chunks, key=lambda c: _section_key(c["section"]))


def _pages(n: int) -> str:
    return "1 página" if n == 1 else f"{n} páginas"


def _doc_line(s: dict[str, Any]) -> str:
    title = f" — {s['title']}" if s["title"] else ""
    return f"- **{s['name']}**{title} ({_pages(s['n_pages'])}, {len(s['sections'])} secciones)"


def _invoice_line(invoices: list[dict[str, Any]]) -> str:
    review = sum(1 for s in invoices if s["status"] == "review")
    names = ", ".join(s["name"] for s in invoices)
    extra = f"; {review} marcadas para revisar" if review else ""
    return f"- {len(invoices)} facturas ({names}{extra})"


def answer_meta(
    cfg: AppConfig, intent: str, docs: list[dict[str, Any]], sources: list[dict[str, Any]]
) -> dict[str, Any]:
    pdfs = [s for s in sources if s["kind"] == "pdf" and s["n_chunks"]]
    invoices = [s for s in sources if s["kind"] == "invoice"]
    citations: list[dict[str, Any]] = []
    lines: list[str] = []

    if intent == "document":
        for s in docs:
            chunks = _section_chunks(cfg, s["id"])
            lines.append(f"**{s['name']}**" + (f" — {s['title']}" if s["title"] else ""))
            lines.append(
                f"{_pages(s['n_pages'])} y {len(chunks)} secciones indexadas. Sus apartados son:"
            )
            for c in chunks:
                pages = ", ".join(str(p) for p in c["pages"])
                lines.append(f"- {c['heading']} (p. {pages})")
                citations.append(_citation(c))
            lines.append("")
        lines.append(
            "Es un índice de apartados, no un resumen del contenido: pregúntame por "
            "cualquiera de ellos y te respondo con la cita exacta."
        )
        return _result("meta:document", "\n".join(lines).strip(), citations)

    if not pdfs and not invoices:
        return _result(
            f"meta:{intent}",
            "Todavía no hay fuentes indexadas. Sube PDFs técnicos o imágenes de facturas "
            "en Fuentes y podré responder sobre ellos citando documento, sección y página.",
            [],
        )

    if intent == "capabilities":
        lines.append(
            "Respondo preguntas sobre las fuentes indexadas y cito siempre documento, "
            "sección, página y el fragmento literal. Si algo no está en las fuentes, "
            "te lo digo en vez de inventarlo."
        )
        lines.append("")
        lines.append("Puedo ayudarte con:")
        if pdfs:
            lines.append(
                f"- Datos concretos de los {len(pdfs)} documentos técnicos, con la cita exacta."
            )
            lines.append("- El índice de apartados de un documento («¿de qué trata <documento>?»).")
        if invoices:
            lines.append(
                f"- Campos de {len(invoices)} facturas (número, fechas, emisor, importes, IVA)."
            )
        lines.append("- Qué fuentes hay («¿qué documentos tienes?»).")
        examples = []
        for s in pdfs[:3]:
            chunks = _section_chunks(cfg, s["id"])
            if chunks:
                c = chunks[min(1, len(chunks) - 1)]
                examples.append(f"- «¿Qué dice {s['name']} sobre {c['heading']}?»")
                citations.append(_citation(c))
        if invoices:
            examples.append(f"- «¿Cuál es el importe total de la factura {invoices[0]['name']}?»")
        if examples:
            lines.append("")
            lines.append("Ejemplos con las fuentes actuales:")
            lines.extend(examples)
        return _result("meta:capabilities", "\n".join(lines), citations)

    lines.append("Estas son las fuentes indexadas:")
    for s in pdfs:
        lines.append(_doc_line(s))
        chunks = _section_chunks(cfg, s["id"])
        if chunks:
            lines.append("  Apartados: " + "; ".join(c["heading"] for c in chunks))
            citations.extend(_citation(c) for c in chunks)
    if invoices:
        lines.append(_invoice_line(invoices))
    lines.append("")
    lines.append("Pregúntame por cualquier apartado y te respondo con la cita exacta.")
    return _result("meta:inventory", "\n".join(lines), citations)


def _result(reason: str, answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": True,
        "answer": answer,
        "citations": citations,
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
