"""Extracción PDF y troceado por secciones numeradas / factura."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pdfplumber

HDR = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(\S.*)$")
FOOT = re.compile(r"^[^·\n]{2,40} · .* \d+$")

# Conservative byte budget leaves room for tokenizer and model special tokens.
PDF_EMBED_BYTES = 480


def ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def pdf_doc_id(name: str) -> str:
    return "pdf-" + hashlib.sha256(name.encode()).hexdigest()[:12]


def invoice_doc_id(number: str) -> str:
    return "inv-" + hashlib.sha256(number.encode()).hexdigest()[:12]


def chunk_id_for(doc: str, section: str, body: str) -> str:
    return hashlib.sha1(f"{doc}|{section}|{body}".encode()).hexdigest()[:12]


def extract_pdf_text(path: str | Path) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"n": i, "text": text})
    return pages


def chunk_pdf(path: str | Path, doc: str | None = None) -> list[dict[str, Any]]:
    path = Path(path)
    doc = doc or pdf_doc_id(path.stem)
    pages = extract_pdf_text(path)
    out: list[dict[str, Any]] = []
    title: str | None = None
    cur: dict[str, Any] | None = None

    for pg in pages:
        for line in (pg["text"] or "").split("\n"):
            line = line.rstrip()
            if not line:
                continue
            if FOOT.match(line):
                continue
            if title is None:
                title = line
                continue
            m = HDR.match(line)
            if m and len(line) < 80:
                if cur:
                    out.append(cur)
                cur = {
                    "doc": doc,
                    "section": m.group(1),
                    "heading": line,
                    "page": pg["n"],
                    "pages": {pg["n"]},
                    "lines": [],
                }
            elif cur is not None:
                cur["lines"].append((line, pg["n"]))
                cur["pages"].add(pg["n"])
            elif not line.startswith("Código"):
                cur = {
                    "doc": doc,
                    "section": "0",
                    "heading": title,
                    "page": pg["n"],
                    "pages": {pg["n"]},
                    "lines": [(line, pg["n"])],
                }

    if cur:
        out.append(cur)

    for c in out:
        c.setdefault("title", title or doc)

    res: list[dict[str, Any]] = []
    for c in out:

        def limit(text: str, size: int) -> str:
            return text.encode("utf-8")[:size].decode("utf-8", errors="ignore")

        prefix = f"[{limit(c['doc'], 32)} · {limit(c['title'], 64)} · {limit(c['heading'], 48)}]"
        budget = PDF_EMBED_BYTES - len((prefix + " ").encode("utf-8"))
        part: list[tuple[str, int]] = []
        size = 0

        def emit(c: dict[str, Any] = c, prefix: str = prefix) -> None:
            nonlocal part, size
            if not part:
                return
            body = " ".join(word for word, _ in part)
            cid = chunk_id_for(c["doc"], f"{c['section']}:{len(res)}", body)
            res.append(
                {
                    "chunk_id": cid,
                    "doc": c["doc"],
                    "section": c["section"],
                    "heading": c["heading"],
                    "title": c["title"],
                    "display_doc": path.stem,
                    "pages": sorted({page for _, page in part}),
                    "body": body,
                    "text": prefix + " " + body,
                }
            )
            part, size = [], 0

        for line, page in c["lines"]:
            for word in line.split():
                while word:
                    room = budget - size - bool(part)
                    if len(word.encode("utf-8")) <= room:
                        size += len(word.encode("utf-8")) + bool(part)
                        part.append((word, page))
                        break
                    if part:
                        emit()
                        continue
                    piece = limit(word, budget)
                    part.append((piece, page))
                    emit()
                    word = word[len(piece) :]
        emit()
    return res


def _make_chunk(
    doc: str, section: str, body: str, *, title: str, heading: str | None = None
) -> dict[str, Any]:
    heading = heading or section
    prefix = f"[{doc} · {title} · {heading}]"
    return {
        "chunk_id": chunk_id_for(doc, section, body),
        "doc": doc,
        "section": section,
        "heading": heading,
        "title": title,
        "pages": [1],
        "body": body,
        "text": prefix + " " + body,
    }


HEADER_KEYS = (
    "numero",
    "fecha_emision",
    "emisor",
    "nif_emisor",
    "cliente",
    "nif_cliente",
    "importe_total",
)


def chunk_invoice(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Un trozo por campo no nulo + uno por línea de factura."""
    number = str(data.get("numero") or data.get("invoice_id") or "factura")
    doc = invoice_doc_id(number)
    title = f"Factura {number}"
    chunks: list[dict[str, Any]] = []

    # Header chunk: questions such as "who issued it and with which tax id"
    # need several fields at once, so they must live in one citable chunk.
    header = [f"{k}: {data[k]}" for k in HEADER_KEYS if data.get(k) not in (None, "")]
    if header:
        body = f"Factura {number}. " + "; ".join(header)
        chunks.append(_make_chunk(doc, "cabecera", body, title=title, heading="cabecera"))

    for key, value in data.items():
        if key in ("numero", "invoice_id", "lineas", "lines"):
            continue
        if value is None or value == "":
            continue
        body = f"{key}: {value}"
        chunks.append(_make_chunk(doc, key, body, title=title, heading=key))

    lines = data.get("lineas") or data.get("lines") or []
    for i, line in enumerate(lines, start=1):
        if isinstance(line, dict):
            parts = [f"{k}: {v}" for k, v in line.items() if v is not None and v != ""]
            body = f"linea {i}: " + "; ".join(parts)
        else:
            body = f"linea {i}: {line}"
        section = f"linea_{i}"
        chunks.append(_make_chunk(doc, section, body, title=title, heading=section))

    for chunk in chunks:
        chunk["display_doc"] = number
    return chunks
