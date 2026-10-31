"""Structured invoice lookup: the LLM only translates the question into a small
plan (JSON); code runs it over an SQLite table of InvoiceRecord rows and builds
the answer with a locator per value (invoice number + field). Absent invoice or
null field -> refusal. The LLM never sees or writes SQL."""

from __future__ import annotations

import sqlite3
from decimal import Decimal, InvalidOperation
from typing import Any

FIELDS = {
    "numero": "número", "fecha_emision": "fecha de emisión", "fecha_vencimiento": "fecha de vencimiento",
    "emisor": "emisor", "nif_emisor": "NIF del emisor", "cliente": "cliente", "nif_cliente": "NIF del cliente",
    "base_imponible_total": "base imponible", "cuota_iva_total": "cuota de IVA", "irpf_tipo": "tipo de IRPF",
    "irpf_importe": "retención IRPF", "recargo_total": "recargo de equivalencia", "importe_total": "importe total",
    "iban": "IBAN",
}
NUMERIC = {"base_imponible_total", "cuota_iva_total", "irpf_importe", "recargo_total", "importe_total", "irpf_tipo"}

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
        self.con.execute(f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, PRIMARY KEY(numero))")

    def upsert(self, rec: dict[str, Any], fichero: str = "", cuadra: str = "") -> None:
        vals = [None if rec.get(k) in (None, "") else str(rec[k]) for k in FIELDS]
        q = ",".join("?" * (len(FIELDS) + 2))
        self.con.execute(f"INSERT OR REPLACE INTO facturas VALUES ({q})", [*vals, fichero, cuadra])
        self.con.commit()

    def rows(self) -> list[dict[str, Any]]:
        cur = self.con.execute("SELECT * FROM facturas ORDER BY numero")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]


def _dec(v: Any) -> Decimal | None:
    import re
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v).replace(" ", "")) if v is not None else None
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", "."))
    except (InvalidOperation, TypeError):
        return None


def _norm_num(s: str | None) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def run_plan(db: InvoiceDB, plan: dict[str, Any]) -> dict[str, Any]:
    """Returns {ok, answer, citations:[{numero, campo, valor}], reason}."""
    rows = db.rows()
    kind = plan.get("kind")
    def refuse(why: str) -> dict[str, Any]:
        return {"ok": False, "answer": None, "citations": [], "reason": why}
    if kind == "campos":
        want = _norm_num(plan.get("numero"))
        hit = [r for r in rows if want and _norm_num(r["numero"]) == want]
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
        return {"ok": True, "answer": f"Factura {r['numero']}: {ans}", "citations": cits, "reason": "sql"}
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
                return op == "=" and (val or "").lower() in x.lower()
            sel = [r for r in rows if keep(r)]
        def loc(r: dict[str, Any], c: str) -> dict[str, Any]:
            return {"numero": r["numero"], "campo": c, "valor": r.get(c)}
        if kind == "contar":
            return {"ok": True, "answer": f"{len(sel)} facturas", "reason": "sql",
                    "citations": [loc(r, f or "numero") for r in sel]}
        if kind == "sumar":
            c = (plan.get("campos") or ["importe_total"])[0]
            if c not in NUMERIC:
                return refuse("campo_no_numerico")
            vals = [(r, _dec(r.get(c))) for r in sel if r.get(c) is not None]
            total = sum((v for _, v in vals if v is not None), Decimal(0))
            return {"ok": True, "answer": f"Suma de {FIELDS[c]}: {total} EUR en {len(vals)} facturas",
                    "reason": "sql", "citations": [loc(r, c) for r, _ in vals]}
        if not sel:
            return {"ok": True, "answer": "Ninguna factura cumple la condición", "citations": [], "reason": "sql_vacio"}
        return {"ok": True, "answer": "Facturas: " + ", ".join(r["numero"] for r in sel), "reason": "sql",
                "citations": [loc(r, f or "numero") for r in sel]}
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
