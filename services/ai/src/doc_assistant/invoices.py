"""Structured invoice lookup: the LLM only translates the question into a small
plan (JSON); code runs it over an SQLite table of InvoiceRecord rows and builds
the answer with a locator per value (invoice number + field). Absent invoice or
null field -> refusal. The LLM never sees or writes SQL."""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from doc_assistant.adapters import LLM, Embedder, OcrPort, build_adapters, build_ocr
from doc_assistant.chunking import chunk_invoice, invoice_doc_id
from doc_assistant.config import load_config
from doc_assistant.invoice_extract import extract_invoice, parse_es_decimal
from doc_assistant.store import ChunkStore

FIELDS = {
    "numero": "número",
    "fecha_emision": "fecha de emisión",
    "fecha_vencimiento": "fecha de vencimiento",
    "emisor": "emisor",
    "nif_emisor": "NIF del emisor",
    "cliente": "cliente",
    "nif_cliente": "NIF del cliente",
    "base_imponible_total": "base imponible",
    "cuota_iva_total": "cuota de IVA",
    "irpf_tipo": "tipo de IRPF",
    "irpf_importe": "retención IRPF",
    "recargo_total": "recargo de equivalencia",
    "importe_total": "importe total",
    "iban": "IBAN",
}
NUMERIC = {
    "base_imponible_total",
    "cuota_iva_total",
    "irpf_importe",
    "recargo_total",
    "importe_total",
    "irpf_tipo",
}

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["documentos", "campos", "filtro", "contar", "sumar"]},
        "numero": {"type": ["string", "null"]},
        "campos": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
        "filtro_campo": {"type": ["string", "null"], "enum": [None, *FIELDS]},
        "filtro_op": {"type": ["string", "null"], "enum": [None, ">", "<", "=", "no_nulo"]},
        "filtro_valor": {"type": ["string", "null"]},
    },
    "required": ["kind", "numero", "campos", "filtro_campo", "filtro_op", "filtro_valor"],
}

PLAN_PROMPT = (
    "Traduce la pregunta a un plan JSON. kind=documentos si pregunta por manuales o equipos, no por facturas. "
    "kind=campos para datos de UNA factura (pon numero tal cual aparece y los campos pedidos). "
    "kind=filtro para listar facturas que cumplen una condición; contar/sumar para agregados "
    "(sumar: campos=[campo a sumar]); 'cuántas' es contar. filtro_valor es solo el número o texto, sin llaves. 'tiene X' es filtro_op=no_nulo. Personas: emisor emite la factura, cliente la recibe. Valores numéricos con punto decimal. Campos válidos: "
    + ", ".join(f"{k} ({v})" for k, v in FIELDS.items())
)


class InvoiceDB:
    def __init__(self, path: str = ":memory:") -> None:
        self.con = sqlite3.connect(path)
        cols = ", ".join(f"{k} TEXT" for k in FIELDS)
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
        )

    def upsert(
        self,
        rec: dict[str, Any],
        fichero: str = "",
        cuadra: str = "",
        motivo: str | None = None,
        *,
        commit: bool = True,
    ) -> None:
        vals = [None if rec.get(k) in (None, "") else str(rec[k]) for k in FIELDS]
        q = ",".join("?" * (len(FIELDS) + 3))
        self.con.execute(
            f"INSERT OR REPLACE INTO facturas VALUES ({q})", [*vals, fichero, cuadra, motivo]
        )
        if commit:
            self.con.commit()

    def rows(self) -> list[dict[str, Any]]:
        cur = self.con.execute("SELECT * FROM facturas ORDER BY numero")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def get(self, numero: str) -> dict[str, Any] | None:
        want = _norm_num(numero)
        rows = self.rows()
        exact = [row for row in rows if row["numero"] == numero]
        hits = exact or [row for row in rows if want and _norm_num(row["numero"]) == want]
        return hits[0] if len(hits) == 1 else None


_dec = parse_es_decimal


def _norm_num(s: str | None) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def run_plan(db: InvoiceDB, plan: dict[str, Any]) -> dict[str, Any]:
    """Returns {ok, answer, citations:[{numero, campo, valor}], reason}."""
    rows = db.rows()
    kind = plan.get("kind")

    def warning(selected: list[dict[str, Any]]) -> str:
        review = [r["numero"] for r in selected if r["cuadra"] == "0"]
        return " Nota: facturas pendientes de revisión: " + ", ".join(review) if review else ""

    def refuse(why: str) -> dict[str, Any]:
        return {"ok": False, "answer": None, "citations": [], "reason": why}

    if kind == "campos":
        want = _norm_num(plan.get("numero"))
        exact = [r for r in rows if r["numero"] == plan.get("numero")]
        hit = exact or [r for r in rows if want and _norm_num(r["numero"]) == want]
        if len(hit) > 1:
            return refuse("factura_ambigua")
        if not hit:
            return refuse("factura_no_encontrada")
        r = hit[0]
        campos = [c for c in plan.get("campos") or [] if c in FIELDS]
        if not campos:
            return refuse("sin_campos")
        missing = [c for c in campos if r.get(c) is None]
        if missing:
            return refuse("campo_ausente:" + ",".join(missing))
        cits = [{"numero": r["numero"], "campo": c, "valor": r[c]} for c in campos]
        ans = "; ".join(f"{FIELDS[c]}: {r[c]}" for c in campos)
        return {
            "ok": True,
            "answer": f"Factura {r['numero']}: {ans}" + warning([r]),
            "citations": cits,
            "reason": "sql",
        }
    if kind in ("filtro", "contar", "sumar"):
        f, op, val = plan.get("filtro_campo"), plan.get("filtro_op"), plan.get("filtro_valor")
        if f and op in (">", "<", "=") and (val is None or (f in NUMERIC and _dec(val) is None)):
            # comparison without a usable value: "tienen IRPF" means non-null; anything else is unanswerable
            if op == ">" and f in NUMERIC and val is None:
                op = "no_nulo"
            else:
                return refuse("filtro_sin_valor")
        sel = rows
        if f:
            if f not in FIELDS:
                return refuse("filtro_invalido")

            def keep(r: dict[str, Any]) -> bool:
                x = r.get(f)
                if op == "no_nulo":
                    return x is not None
                if x is None:
                    return False
                if f in NUMERIC and op in (">", "<", "="):
                    a, b = _dec(x), _dec(val)
                    if a is None or b is None:
                        return False
                    return a > b if op == ">" else a < b if op == "<" else a == b
                return op == "=" and (val or "").strip().casefold() == x.strip().casefold()

            sel = [r for r in rows if keep(r)]

        def loc(r: dict[str, Any], c: str) -> dict[str, Any]:
            return {"numero": r["numero"], "campo": c, "valor": r.get(c)}

        if kind == "contar":
            return {
                "ok": True,
                "answer": f"{len(sel)} facturas" + warning(sel),
                "reason": "sql",
                "citations": [loc(r, f or "numero") for r in sel],
            }
        if kind == "sumar":
            c = (plan.get("campos") or ["importe_total"])[0]
            if c not in NUMERIC:
                return refuse("campo_no_numerico")
            vals = [(r, _dec(r.get(c))) for r in sel]
            if any(v is None for _, v in vals):
                return refuse("suma_datos_incompletos")
            total = sum((v for _, v in vals if v is not None), Decimal(0))
            return {
                "ok": True,
                "answer": f"Suma de {FIELDS[c]}: {total} EUR en {len(vals)} facturas"
                + warning(sel),
                "reason": "sql",
                "citations": [loc(r, c) for r, _ in vals],
            }
        if not sel:
            return {
                "ok": True,
                "answer": "Ninguna factura cumple la condición",
                "citations": [],
                "reason": "sql_vacio",
            }
        return {
            "ok": True,
            "answer": "Facturas: " + ", ".join(r["numero"] for r in sel) + warning(sel),
            "reason": "sql",
            "citations": [loc(r, f or "numero") for r in sel],
        }
    return refuse("no_es_factura")


def is_invoice_question(q: str, db: InvoiceDB) -> bool:
    """Deterministic router: SQL path only if the question names invoices, an invoice
    number, or a party present in the table. Everything else goes to document RAG."""
    low = q.lower()
    if any(w in low for w in ("factura", "irpf", "iva", "emisor", "importe", "nif", "iban")):
        return True
    norm = _norm_num(q)
    for r in db.rows():
        if r["numero"] and _norm_num(r["numero"]) in norm:
            return True
        for c in ("emisor", "cliente"):
            if r.get(c) and r[c].lower() in low:
                return True
    return False


def sanitize_image_filename(name: str, numero: str) -> str:
    base = Path(name or f"{numero}.png").name
    safe = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._") or numero
    lower = safe.lower()
    if not lower.endswith((".png", ".jpg", ".jpeg")):
        safe = f"{safe}.png"
    return safe


def upload_invoice(
    config_path: str | Path,
    image: bytes,
    filename: str,
    *,
    ocr: OcrPort | None = None,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
) -> dict[str, Any]:
    """Extract, persist SQL row, index chunks+image in the same retrieval store."""
    cfg = load_config(config_path)
    if ocr is None:
        ocr = build_ocr(cfg)
    if embedder is None or llm is None:
        emb, _, default_llm = build_adapters(cfg, fake=False)
        embedder = embedder or emb
        llm = llm or default_llm

    extracted = extract_invoice(image, ocr=ocr, llm=llm)
    record = extracted["record"]
    numero = record.get("numero")
    if not numero:
        return {
            "record": record,
            "estado": "revisar",
            "motivo": "sin_numero",
            "evidencias": extracted["evidencias"],
            "flags": extracted["flags"],
        }

    chunks = chunk_invoice(record)
    embeddings = embedder.embed([c["text"] for c in chunks]) if chunks else []

    invoices_dir = cfg.data_dir / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    path = invoices_dir / (
        invoice_doc_id(numero) + Path(sanitize_image_filename(filename, numero)).suffix
    )
    relative = str(path.relative_to(cfg.data_dir))
    fd, temporary = tempfile.mkstemp(dir=invoices_dir, prefix=".invoice-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image)
        dim = getattr(embedder, "dim", None) or cfg.embeddings.dim or 8
        store = ChunkStore(cfg.db, dim=dim)
        try:
            cols = ", ".join(f"{k} TEXT" for k in FIELDS)
            store.db.execute(
                f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
            )
            values = [None if record.get(k) in (None, "") else str(record[k]) for k in FIELDS]
            placeholders = ",".join("?" * (len(FIELDS) + 3))
            store.db.execute(
                f"INSERT OR REPLACE INTO facturas VALUES ({placeholders})",
                [
                    *values,
                    relative,
                    "1" if extracted["estado"] == "ok" else "0",
                    extracted["motivo"],
                ],
            )
            store.replace_document(
                invoice_doc_id(numero), chunks, embeddings, [image], commit=False
            )
            store.db.commit()
        except Exception:
            store.db.rollback()
            raise
        finally:
            store.db.close()
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return {
        "record": record,
        "estado": extracted["estado"],
        "motivo": extracted["motivo"],
        "evidencias": extracted["evidencias"],
        "flags": extracted["flags"],
        "fichero": relative,
    }


def invoice_image(config_path: str | Path, invoice_id: str) -> bytes | None:
    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    try:
        row = db.get(invoice_id)
    finally:
        db.con.close()
    if row is None:
        return None
    store = ChunkStore(cfg.db, dim=cfg.embeddings.dim or 8)
    try:
        png = store.page(invoice_doc_id(row["numero"]), 1)
    finally:
        store.db.close()
    if png is not None:
        return png
    fichero = row.get("fichero") or ""
    if fichero:
        path = cfg.data_dir / fichero
        if path.is_file():
            return path.read_bytes()
    return None


def ask_invoices(
    config_path: str | Path,
    question: str,
    *,
    llm: LLM,
) -> dict[str, Any] | None:
    """If the question is about invoices, run the SQL plan path; else return None."""
    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    try:
        if not is_invoice_question(question, db):
            return None
        plan = llm.chat(
            [
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": question},
            ],
            schema=PLAN_SCHEMA,
        )
        if plan.get("kind") == "documentos":
            return None
        result = run_plan(db, plan)
    finally:
        db.con.close()

    citations = []
    for cit in result.get("citations") or []:
        valor = cit.get("valor")
        fragment = "" if valor is None else str(valor)
        citations.append(
            {
                "chunk_id": f"{cit.get('numero')}:{cit.get('campo')}",
                "quote": fragment,
                "doc": cit.get("numero") or "",
                "doc_id": invoice_doc_id(cit.get("numero") or ""),
                "section": cit.get("campo") or "",
                "pages": [1],
                "fragment": fragment,
            }
        )
    if result.get("ok"):
        return {
            "ok": True,
            "answer": result.get("answer") or "",
            "citations": citations,
            "reason": result.get("reason") or "sql",
            "latencies": {},
            "raw": plan,
        }
    return {
        "ok": False,
        "answer": "No dispongo de esa información en los documentos",
        "citations": [],
        "reason": f"invoice:{result.get('reason')}",
        "latencies": {},
        "raw": plan,
    }
