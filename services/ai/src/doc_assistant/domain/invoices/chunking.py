from typing import Any

from doc_assistant.domain.documents.ids import chunk_id_for, invoice_doc_id


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
