"""Invoice questions -> validated plan -> code-built SQL -> grounded answer.

The LLM only fills a small JSON plan (schema below). Code validates and normalises it,
resolves numbers, NIFs and party names against the derived index (accents, case,
partial names, typos), builds parametrised SQL over a closed list of columns, and
writes the answer from the selected rows. Rules:
- a question for a value gets values, never a bare list of invoice numbers;
- citations come only from the selected invoices and the fields shown;
- ambiguity yields a clarification with the real candidates; absence yields a refusal;
- one retry when the plan does not validate, then refusal. No fallback to document RAG."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from doc_assistant.adapters import AdapterBusy, AdapterError, AdapterTimeout
from doc_assistant.chunking import invoice_doc_id
from doc_assistant.invoice_fields import (
    FIELD_SPECS,
    asks_for,
    display_value,
    format_eur,
    labels_for,
    noun_phrase,
    prune_unasked,
)
from doc_assistant.invoice_index import (
    AMOUNT_COLS,
    DATE_COLS,
    NIF_RE,
    Party,
    fold,
    norm_key,
    parse_amount,
    parse_date_range,
    party_tokens,
    resolve_nif,
    resolve_number,
    resolve_party,
)

FIELDS = {key: spec.label for key, spec in FIELD_SPECS.items()}
NUMERIC = set(AMOUNT_COLS)
FILTERABLE = [*AMOUNT_COLS, *DATE_COLS]
INTENTS = ["valor", "lista", "contar", "sumar", "documentos"]
OPS = {">": ">", "<": "<", ">=": ">=", "<=": "<=", "=": "="}
MAX_VALUES = 10
MAX_LIST = 20

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        "numero": {"type": ["string", "null"]},
        "parte": {"type": ["string", "null"]},
        "campos": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
        "filtros": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "campo": {"type": "string", "enum": FILTERABLE},
                    "op": {"type": "string", "enum": list(OPS)},
                    "valor": {"type": "string"},
                },
                "required": ["campo", "op", "valor"],
            },
        },
        "fecha_desde": {"type": ["string", "null"]},
        "fecha_hasta": {"type": ["string", "null"]},
        "tiene": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
    },
    # Only intent is required: omitted keys mean "not asked", and every omitted key is
    # a dozen tokens the model does not have to generate (~115 ms each on a laptop).
    "required": ["intent"],
}

PLAN_PROMPT = (
    "Traduce la pregunta sobre facturas a un plan JSON. No respondas la pregunta.\n"
    "- intent: valor = pide uno o varios datos (total, IVA, fecha, NIF...) de una factura o de "
    "las facturas de alguien; lista = pide qué facturas cumplen algo; contar = cuántas; "
    "sumar = suma de un importe (campos=[importe]); documentos = no trata de facturas sino "
    "de manuales o equipos.\n"
    "- numero: el número de factura tal como aparece, o null. Nunca pongas un nombre aquí.\n"
    "- parte: nombre de persona o empresa, o NIF, tal como aparece en la pregunta, o null.\n"
    "- campos: datos pedidos. 'precio final', 'total', 'cuánto' = importe_total.\n"
    "- filtros: solo comparaciones de importe o fecha ('más de 1000 €' -> "
    "{campo: importe_total, op: '>', valor: '1000'}). valor solo con el número.\n"
    "- fecha_desde/fecha_hasta: AAAA-MM-DD; un mes entero = primer y último día; un día = "
    "ambas iguales.\n"
    "- tiene: campos que deben existir ('con IRPF' -> [irpf_importe]).\n"
    "Campos: " + ", ".join(f"{k} ({v})" for k, v in FIELDS.items()) + "\n"
    "Omite las claves que no apliquen.\nEjemplos:\n"
    "'total de la factura de Ana Ruiz' -> {intent: valor, parte: 'Ana Ruiz', campos: [importe_total]}\n"
    "'IVA de la F-12' -> {intent: valor, numero: 'F-12', campos: [cuota_iva_total]}\n"
    "'facturas de más de 500 euros' -> {intent: lista, filtros: [{campo: importe_total, op: '>', "
    "valor: '500'}]}\n"
    "'¿cuántas facturas de marzo de 2025?' -> {intent: contar, fecha_desde: '2025-03-01', "
    "fecha_hasta: '2025-03-31'}\n"
    "'suma del IVA de las facturas de Talleres Sur' -> {intent: sumar, parte: 'Talleres Sur', "
    "campos: [cuota_iva_total]}\n"
    "'¿qué facturas tienen IRPF?' -> {intent: lista, tiene: [irpf_importe]}\n"
    "'¿cómo se calibra el sensor?' -> {intent: documentos}"
)

ROLE_CUES = {
    "cliente": (
        "emitida a",
        "emitidas a",
        "emitido a",
        "a nombre de",
        "cliente es",
        "cuyo cliente",
        "recibida",
        "recibidas",
        "recibio",
        "recibido",
        "ha recibido",
        "facturada a",
        "facturadas a",
        "facturado a",
    ),
    "emisor": (
        "emitida por",
        "emitidas por",
        "emitido por",
        "emisor es",
        "cuyo emisor",
        "emisora es",
        "cuya emisora",
        "proveedor",
        "ha emitido",
        "han emitido",
        "emite",
        "pagar a",
        "pagarle",
        "cobra",
        "de parte de",
    ),
}
# Whole words only: 'iva' must not fire on 'explosiva'.
ROUTE_WORDS = (
    "fra",
    "fras",
    "irpf",
    "iva",
    "emisor",
    "importe",
    "nif",
    "cif",
    "iban",
    "base imponible",
    "retencion",
    "recargo",
)


def role_cue(question: str) -> str | None:
    q = f" {fold(question)} "
    spans = [
        (m.start(), m.end(), r)
        for r, cues in ROLE_CUES.items()
        for c in cues
        for m in re.finditer(re.escape(f" {c} "), q)
    ]
    # 'han emitido a X': overlapping cues, the one that reaches further (the preposition) wins
    kept = {
        r
        for a, b, r in spans
        if not any(a2 < b and a < b2 and b2 > b and r2 != r for a2, b2, r2 in spans)
    }
    return kept.pop() if len(kept) == 1 else None


def is_invoice_question(question: str, con: sqlite3.Connection) -> bool:
    """SQL path if the question names invoices, an invoice number, a NIF or a known party."""
    q = f" {fold(question)} "
    if " factur" in q or any(f" {w} " in q for w in ROUTE_WORDS):
        return True
    if NIF_RE.search(question) and resolve_nif(con, NIF_RE.search(question).group(0)):  # type: ignore[union-attr]
        return True
    for tok in re.findall(r"[0-9A-Za-z][0-9A-Za-z/\-]*\d[0-9A-Za-z/\-]*", question):
        if re.search(r"[A-Za-z/\-]", tok) and resolve_number(con, tok):
            return True
    if set(q.split()) & party_tokens(con):
        return True
    # typos in a name ('Lucai Martn'): two fuzzy token hits on one party
    return any(p.matched >= 2 for p in resolve_party(con, question))


# --- plan validation -------------------------------------------------------------


@dataclass
class Plan:
    intent: str
    numero: str | None = None
    parte: str | None = None
    campos: list[str] = field(default_factory=list)
    filtros: list[tuple[str, str, Any]] = field(default_factory=list)  # (col, op, typed value)
    desde: str | None = None
    hasta: str | None = None
    tiene: list[str] = field(default_factory=list)
    sin_anio: bool = False  # dates compare on MM-DD only


def validate_plan(raw: Any) -> tuple[Plan | None, list[str]]:
    """Schema + semantic checks. Values are normalised (amounts to cents, dates ISO)."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, ["el plan no es un objeto"]
    intent = raw.get("intent")
    if intent not in INTENTS:
        return None, [f"intent inválido: {intent!r}"]
    plan = Plan(intent=intent)
    for key in ("numero", "parte"):
        v = raw.get(key)
        if v is not None and not isinstance(v, str):
            errors.append(f"{key} debe ser texto")
        elif v and v.strip() and fold(v) not in ("null", "none", "ninguno"):
            setattr(plan, key, v.strip().strip("{}'\"").strip())
    for key in ("campos", "tiene"):
        vals = raw.get(key) or []
        if not isinstance(vals, list) or any(v not in FIELDS for v in vals):
            errors.append(f"{key} contiene campos inválidos")
        else:
            setattr(plan, key, list(dict.fromkeys(vals)))
    for f in raw.get("filtros") or []:
        if not isinstance(f, dict) or f.get("campo") not in FILTERABLE or f.get("op") not in OPS:
            errors.append(f"filtro inválido: {f!r}")
            continue
        campo, op, valor = f["campo"], f["op"], f.get("valor")
        if campo in AMOUNT_COLS:
            d = parse_amount(valor)
            if d is None:
                errors.append(f"filtro {campo}: '{valor}' no es un importe")
                continue
            plan.filtros.append((AMOUNT_COLS[campo], op, int((d * 100).to_integral_value())))
        else:
            rng = parse_date_range(valor)
            if rng is None:
                errors.append(f"filtro {campo}: '{valor}' no es una fecha")
                continue
            col = DATE_COLS[campo]
            if op == "=":
                plan.filtros += [(col, ">=", rng[0]), (col, "<=", rng[1])]
            elif op in (">", "<="):
                plan.filtros.append((col, op, rng[1]))
            else:
                plan.filtros.append((col, op, rng[0]))
    for key, idx in (("fecha_desde", 0), ("fecha_hasta", 1)):
        v = raw.get(key)
        if v in (None, ""):
            continue
        rng = parse_date_range(v)
        if rng is None:
            errors.append(f"{key}: '{v}' no es una fecha")
        else:
            setattr(plan, "desde" if idx == 0 else "hasta", rng[idx])
    if plan.desde and not plan.hasta and raw.get("fecha_desde"):
        rng = parse_date_range(raw["fecha_desde"])
        if rng and rng[0] != rng[1]:
            plan.hasta = rng[1]  # 'marzo 2026' in fecha_desde means the month
    if intent == "sumar" and plan.campos and plan.campos[0] not in NUMERIC:
        errors.append("sumar necesita un importe en campos")
    return (plan if not errors else None), errors


# --- selection ---------------------------------------------------------------------


@dataclass
class Selection:
    numeros: list[str] | None = None  # None = no restriction
    party: Party | None = None
    rol: str | None = None
    label: str = ""
    selector_fields: list[str] = field(default_factory=list)
    stop: dict[str, Any] | None = None  # clarification or refusal decided while resolving


def _looks_numberish(s: str) -> bool:
    return bool(re.search(r"\d", s))


MAX_CANDIDATES = 5
SUMMARY_FIELDS = ["importe_total", "fecha_emision", "emisor", "cliente"]
KEY_DATA_FIELDS = ["emisor", "cliente", "numero", "fecha_emision", "importe_total"]
CLARIFY_PROMPT = "¿De qué factura?"


def followup_fields(plan: Plan, question: str) -> list[str]:
    """Fields to ask again for once the invoice is chosen. Only a value question carries
    its fields over; any other intent asks for the invoice's data."""
    if plan.intent != "valor":
        return []
    asked = [c for c in (plan.campos or lexical_fields(question, None)) if c != "numero"]
    return prune_unasked(asked, question)[:3]


def followup_question(fields: list[str], numero: str, question: str = "") -> str:
    """The original question with the invoice named, written from the fields asked and
    with the question's own words for them."""
    if not fields:
        return f"¿Qué datos tiene la factura {numero}?"
    nouns = [noun_phrase(c, question) for c in fields]
    joined = nouns[0] if len(nouns) == 1 else ", ".join(nouns[:-1]) + " y " + nouns[-1]
    verb = "Cuál es" if len(nouns) == 1 else "Cuáles son"
    return f"¿{verb} {joined} de la factura {numero}?"


def _candidates_answer(
    con: sqlite3.Connection,
    numeros: list[str],
    text: str,
    why: str,
    fields: list[str],
    detail: str | None = None,
    question: str = "",
) -> dict[str, Any]:
    """Ambiguity: the real candidate invoices, as structured data plus a plain-text fallback."""
    rows = _rows(con, numeros[:MAX_CANDIDATES])
    opts = "; ".join(_describe(r) for r in rows)
    more = f" (y {len(numeros) - MAX_CANDIDATES} más)" if len(numeros) > MAX_CANDIDATES else ""
    return {
        "ok": False,
        "reason": why,
        "answer": f"{text} ¿Te refieres a alguna de estas? {opts}{more}",
        "citations": [],
        "candidates": [r["numero"] for r in rows],
        "clarification": {
            "prompt": CLARIFY_PROMPT,
            "detail": detail,
            "total": len(numeros),
            "candidates": [
                {
                    "numero": r["numero"],
                    "emisor": r.get("emisor"),
                    "cliente": r.get("cliente"),
                    "fecha": r.get("fecha_emision"),
                    "total": _shown(r, "importe_total"),
                    "question": followup_question(fields, r["numero"], question),
                }
                for r in rows
            ],
        },
    }


def _describe(r: dict[str, Any]) -> str:
    bits = [r["numero"]]
    if r.get("emisor"):
        bits.append(f"emisor {r['emisor']}")
    if r.get("cliente"):
        bits.append(f"cliente {r['cliente']}")
    if r.get("fecha_emision"):
        bits.append(str(r["fecha_emision"]))
    return ", ".join(bits)


def _refuse(why: str, text: str = "") -> dict[str, Any]:
    return {"ok": False, "reason": why, "answer": text, "citations": []}


def select(con: sqlite3.Connection, plan: Plan, question: str) -> Selection:
    sel = Selection()
    numero, parte = plan.numero, plan.parte
    if numero and not _looks_numberish(numero):
        parte, numero = parte or numero, None
    # NIF: from the plan or spotted in the question
    nif_text = None
    for cand in (parte, numero, question):
        m = NIF_RE.search(cand or "")
        if m and resolve_nif(con, m.group(0)):
            nif_text = m.group(0)
            break
    if numero and (nif_text and norm_key(numero) == norm_key(nif_text)):
        numero = None
    if numero is None and not parte and not nif_text:
        for tok in re.findall(r"[0-9A-Za-z][0-9A-Za-z/\-]*\d[0-9A-Za-z/\-]*", question):
            if re.search(r"[A-Za-z/\-]", tok) and resolve_number(con, tok):
                numero = tok
                break
    cue = role_cue(question)
    if numero and parte and not resolve_number(con, numero):
        numero = None  # a stray number next to a name: the name decides
    if numero:
        hits = resolve_number(con, numero)
        if not hits:
            sel.stop = _refuse(
                "factura_no_encontrada", f"No hay ninguna factura con número {numero}."
            )
            return sel
        if len(hits) > 1:
            text = f"Varias facturas encajan con «{numero}»."
            sel.stop = _candidates_answer(
                con, hits, text, "factura_ambigua", followup_fields(plan, question), text, question
            )
            return sel
        sel.numeros, sel.label = hits, f"Factura {hits[0]}"
        return sel
    if nif_text:
        parties = list(resolve_nif(con, nif_text).values())
    elif parte:
        parties = resolve_party(con, parte)
        if not parties:
            sel.stop = _refuse("parte_no_encontrada", f"No hay facturas de «{parte}».")
            return sel
    else:
        parties = resolve_party(con, question)
        if not parties:
            return sel  # no party at all: filters alone decide
    if len(parties) > 1 and (plan.filtros or plan.desde or plan.hasta or plan.tiene):
        fitting = [
            p
            for p in parties
            if query_numeros(
                con, plan, Selection(numeros=sorted(p.numeros(cue) or p.numeros(None)))
            )
        ]
        if len(fitting) == 1:
            parties = fitting  # 'Lucía del 7 de marzo': only one Lucía has that invoice
    if len(parties) > 1:
        nums = sorted(set().union(*(p.numeros(cue) or p.numeros(None) for p in parties)))
        names = " o ".join(f"{p.nombre}" + (f" ({p.nif})" if p.nif else "") for p in parties[:5])
        text = f"Hay varias personas o empresas que encajan: {names}."
        sel.stop = _candidates_answer(
            con, nums, text, "parte_ambigua", followup_fields(plan, question), text, question
        )
        return sel
    p = parties[0]
    if cue and not p.numeros(cue):
        other = "emisor" if cue == "cliente" else "cliente"
        sel.stop = _refuse(
            "parte_rol_distinto",
            f"{p.nombre} aparece como {other}, no como {cue}, en las facturas.",
        )
        return sel
    rol = cue if cue else (next(iter(p.roles)) if len(p.roles) == 1 else None)
    sel.party, sel.rol = p, rol
    sel.numeros = sorted(p.numeros(rol))
    sel.label = p.nombre
    sel.selector_fields = [rol] if rol else []
    return sel


# --- execution ----------------------------------------------------------------------


def _rows(con: sqlite3.Connection, numeros: list[str]) -> list[dict[str, Any]]:
    if not numeros:
        return []
    cur = con.execute(
        f"SELECT f.*, q.fecha_emision_iso FROM facturas f JOIN facturas_q q USING(numero) "
        f"WHERE numero IN ({','.join('?' * len(numeros))}) "
        "ORDER BY q.fecha_emision_iso, numero",
        numeros,
    )
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def query_numeros(
    con: sqlite3.Connection, plan: Plan, sel: Selection, trace: dict[str, Any] | None = None
) -> list[str]:
    """Builds the WHERE from whitelisted columns only; every value is a parameter."""
    where, params = [], []
    if sel.numeros is not None:
        if not sel.numeros:
            return []
        where.append(f"q.numero IN ({','.join('?' * len(sel.numeros))})")
        params += sel.numeros
    allowed = set(AMOUNT_COLS.values()) | set(DATE_COLS.values())
    for col, op, val in plan.filtros:
        assert col in allowed and op in OPS
        where.append(f"q.{col} {OPS[op]} ?")
        params.append(val)
    date = "substr(q.fecha_emision_iso, 6)" if plan.sin_anio else "q.fecha_emision_iso"
    cut = 5 if plan.sin_anio else 0
    if plan.desde:
        where.append(f"{date} >= ?")
        params.append(plan.desde[cut:])
    if plan.hasta:
        where.append(f"{date} <= ?")
        params.append(plan.hasta[cut:])
    for c in plan.tiene:
        assert c in FIELDS
        col = f"q.{AMOUNT_COLS[c]}" if c in AMOUNT_COLS else f"f.{c}"
        where.append(f"{col} IS NOT NULL" + (" AND " + col + " != 0" if c in AMOUNT_COLS else ""))
    sql = (
        "SELECT q.numero FROM facturas_q q JOIN facturas f USING(numero)"
        + (" WHERE " + " AND ".join(where) if where else "")
        + " ORDER BY q.fecha_emision_iso, q.numero"
    )
    if trace is not None:
        trace["sql"] = sql
        trace["params"] = params.copy()
    return [r[0] for r in con.execute(sql, params)]


def _warning(rows: list[dict[str, Any]]) -> str:
    review = [r["numero"] for r in rows if r.get("cuadra") == "0"]
    return " Nota: facturas pendientes de revisión: " + ", ".join(review) if review else ""


def _cit(r: dict[str, Any], c: str) -> dict[str, Any]:
    return {"numero": r["numero"], "campo": c, "valor": r.get(c)}


ROLE_WORDS = {"emisor", "emisora", "cliente", "proveedor", "destinatario", "receptor"}


# Fallback when the plan omits campos: the small model sometimes drops them.
LEXICAL_FIELDS = (
    (("nif", "cif"), ("nif_emisor", "nif_cliente")),
    (("iban", "cuenta"), ("iban",)),
    (("iva",), ("cuota_iva_total",)),
    (("irpf", "retencion"), ("irpf_importe",)),
    (("recargo",), ("recargo_total",)),
    (("base",), ("base_imponible_total",)),
    (("vencimiento", "vence"), ("fecha_vencimiento",)),
    (("fecha", "cuando"), ("fecha_emision",)),
    (("total", "importe", "cuanto", "precio"), ("importe_total",)),
)


def lexical_fields(question: str, rol: str | None) -> list[str]:
    words = set(fold(question).split())
    out: list[str] = []
    for cues, fields in LEXICAL_FIELDS:
        if words & set(cues):
            picked = fields
            if fields[0] == "nif_emisor" and (rol or words & ROLE_WORDS):
                named = rol
                if words & {"cliente", "destinatario", "receptor"}:
                    named = "cliente"
                elif words & {"emisor", "emisora", "proveedor"}:
                    named = "emisor"
                picked = (f"nif_{named}",)
            out.extend(picked)
    return out


def _role_fields(campos: list[str], rol: str | None, question: str) -> list[str]:
    """'NIF de Lucía' when Lucía is the issuer means nif_emisor: unless the question names
    a role, identity fields (name, NIF) refer to the party that selected the invoice."""
    if not rol or ROLE_WORDS & set(fold(question).split()):
        return campos
    other = "cliente" if rol == "emisor" else "emisor"
    swap = {other: rol, f"nif_{other}": f"nif_{rol}"}
    return list(dict.fromkeys(swap.get(c, c) for c in campos))


YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def fix_years(plan: Plan, question: str) -> None:
    """The model invents years ('marzo' -> 2025-03). Years come from the question only:
    one year in the question overrides the plan; none means any year (month/day match)."""
    if not (plan.desde or plan.hasta):
        return
    years = set(YEAR_RE.findall(question))
    if len(years) == 1:
        y = years.pop()
        plan.desde = plan.desde and y + plan.desde[4:]
        plan.hasta = plan.hasta and y + plan.hasta[4:]
    elif not years:
        plan.sin_anio = True


def execute(
    con: sqlite3.Connection, plan: Plan, question: str, trace: dict[str, Any] | None = None
) -> dict[str, Any]:
    fix_years(plan, question)
    if trace is not None:
        trace["plan"] = asdict(plan)
    sel = select(con, plan, question)
    if trace is not None:
        trace["selection"] = {
            "numeros": sel.numeros,
            "rol": sel.rol,
            "label": sel.label,
            "selector_fields": sel.selector_fields,
            "stop_reason": sel.stop.get("reason") if sel.stop else None,
            "clarification": sel.stop.get("clarification") if sel.stop else None,
        }
    if sel.stop:
        return sel.stop
    has_selector = sel.numeros is not None or bool(
        plan.filtros or plan.desde or plan.hasta or plan.tiene
    )
    numeros = query_numeros(con, plan, sel, trace)
    if trace is not None:
        trace["rows"] = _rows(con, numeros)
    result = _shape(con, plan, sel, numeros, has_selector, question)
    if trace is not None and result.get("clarification"):
        trace["selection"]["stop_reason"] = result.get("reason")
        trace["selection"]["clarification"] = result["clarification"]
    result["selected"] = numeros
    return result


def _shown(r: dict[str, Any], c: str) -> str | None:
    v = r.get(c)
    return None if v in (None, "") else display_value(c, v)


def _pairs(r: dict[str, Any], fields: list[str], labels: dict[str, str]) -> str:
    return "; ".join(f"{labels[c]}: {_shown(r, c)}" for c in fields if _shown(r, c) is not None)


def _row_view(r: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {
        "numero": r["numero"],
        "doc_id": invoice_doc_id(r["numero"]),
        "question": followup_question([], r["numero"]),
        "values": {c: r.get(c) for c in fields},
    }


def _table_view(
    rows: list[dict[str, Any]],
    fields: list[str],
    labels: dict[str, str],
    title: str | None,
    *,
    total: dict[str, str] | None = None,
    truncated: str | None = None,
) -> dict[str, Any]:
    fields = [field for field in fields if field != "numero"]
    return {
        "kind": "table",
        "title": title,
        "fields": fields,
        "labels": labels,
        "rows": [_row_view(r, fields) for r in rows],
        "total": total,
        "truncated": truncated,
        "review": [r["numero"] for r in rows if r.get("cuadra") == "0"],
    }


def _record_view(
    r: dict[str, Any], fields: list[str], labels: dict[str, str], summary: bool
) -> dict[str, Any]:
    return {
        "kind": "record",
        "title": "Datos clave" if summary else f"Factura {r['numero']}",
        "numero": r["numero"],
        "doc_id": invoice_doc_id(r["numero"]),
        "fields": fields,
        "labels": labels,
        "values": {c: r.get(c) for c in fields},
        "available": {c: r.get(c) for c in FIELDS},
        "review": [r["numero"]] if r.get("cuadra") == "0" else [],
    }


def _shape(
    con: sqlite3.Connection,
    plan: Plan,
    sel: Selection,
    numeros: list[str],
    has_selector: bool,
    question: str,
) -> dict[str, Any]:
    scope = f" de {sel.label}" if sel.party else ""
    if plan.intent == "valor":
        if not numeros:
            return _refuse("sin_resultados", "Ninguna factura cumple la condición.")
        if not has_selector and len(numeros) > 1:
            return _candidates_answer(
                con,
                numeros,
                CLARIFY_PROMPT,
                "aclaracion",
                followup_fields(plan, question),
                question=question,
            )
        if len(numeros) > MAX_VALUES:
            text = f"Hay {len(numeros)} facturas{scope}; acota por número o fecha."
            return _candidates_answer(
                con, numeros, text, "aclaracion", followup_fields(plan, question), text, question
            )
        rows = _rows(con, numeros)
        asked = prune_unasked(
            plan.campos or lexical_fields(question, sel.rol), question, party_role=sel.rol
        )
        general_data = (
            re.search(
                r"\bdatos(?: clave)? (?:tiene (?:la )?factura|de (?:la )?factura)\b",
                fold(question),
            )
            is not None
            and not {"numero", "numeros"} & set(fold(question).split())
            and not any(asks_for(c, question, party_role=sel.rol) for c in FIELDS)
        )
        picked = [] if general_data else _role_fields(asked, sel.rol, question)
        campos = picked or (KEY_DATA_FIELDS if len(rows) == 1 else SUMMARY_FIELDS)
        labels = labels_for(campos, question)
        lines, cits, elements, shown_rows = [], [], [], []
        for r in rows:
            got = [c for c in campos if _shown(r, c) is not None]
            if not got:
                continue
            shown_rows.append(r)
            missing = [labels[c] for c in campos if c not in got]
            lines.append(
                f"Factura {r['numero']}: "
                + _pairs(r, got, labels)
                + ("; sin dato de " + ", ".join(missing) if missing else "")
            )
            refs = [_cit(r, c) for c in got]
            elements.append({"text": lines[-1], "citations": refs})
            cits += refs
        if not lines:
            missing_keys = ",".join(campos)
            return _refuse("campo_ausente:" + missing_keys, "Ese dato no consta en la factura.")
        head = f"{sel.label} tiene {len(rows)} facturas. " if sel.party and len(rows) > 1 else ""
        if len(shown_rows) == 1:
            summary = not picked
            fields = KEY_DATA_FIELDS if summary else campos
            view = _record_view(shown_rows[0], fields, {**FIELDS, **labels}, summary)
        else:
            view = _table_view(shown_rows, campos, labels, head.strip() or None)
        return {
            "ok": True,
            "reason": "sql",
            "answer": head + "\n".join(lines) + _warning(rows),
            "headline": head.strip(),
            "view": view,
            "elements": elements,
            "review": [r["numero"] for r in rows if r.get("cuadra") == "0"],
            "citations": cits,
        }
    if plan.intent == "contar":
        rows = _rows(con, numeros[:50])
        n = len(numeros)
        headline = f"{n} factura{'s' if n != 1 else ''}{scope}"
        return {
            "ok": True,
            "reason": "sql",
            "answer": headline + _warning(rows),
            "headline": headline,
            "elements": [
                {"text": f"Factura {r['numero']}", "citations": [_cit(r, "numero")]} for r in rows
            ],
            "review": [r["numero"] for r in rows if r.get("cuadra") == "0"],
            "citations": [_cit(r, "numero") for r in rows],
        }
    if plan.intent == "sumar":
        c = (plan.campos or ["importe_total"])[0]
        if c not in NUMERIC:
            return _refuse("campo_no_numerico")
        if not numeros:
            return _refuse("sin_resultados", "Ninguna factura cumple la condición.")
        rows = _rows(con, numeros)
        vals = [parse_amount(r.get(c)) for r in rows]
        if any(v is None for v in vals):
            return _refuse("suma_datos_incompletos", "Alguna factura no tiene ese importe.")
        total = sum((v for v in vals if v is not None), Decimal(0))
        n = len(rows)
        label = labels_for([c], question)[c]
        headline = (
            f"Suma de {label}{scope}: {format_eur(total)} en {n} factura{'s' if n != 1 else ''}"
        )
        return {
            "ok": True,
            "reason": "sql",
            "answer": headline + _warning(rows),
            "headline": headline,
            "view": _table_view(
                rows,
                [c],
                {c: label},
                f"Suma de {label}{scope}",
                total={"label": "Total", "text": format_eur(total) or ""},
            ),
            "elements": [
                {
                    "text": f"Factura {r['numero']}: {label}: {_shown(r, c)}",
                    "citations": [_cit(r, c)],
                }
                for r in rows
            ],
            "review": [r["numero"] for r in rows if r.get("cuadra") == "0"],
            "citations": [_cit(r, c) for r in rows],
        }
    # lista
    if not numeros:
        return {
            "ok": True,
            "reason": "sql_vacio",
            "answer": "Ninguna factura cumple la condición",
            "headline": "Ninguna factura cumple la condición",
            "citations": [],
        }
    rows = _rows(con, numeros[:MAX_LIST])
    asked = prune_unasked([c for c in plan.campos if c != "numero"], question)
    filt = [
        f
        for f, col in {**AMOUNT_COLS, **DATE_COLS}.items()
        if any(col == fc for fc, _, _ in plan.filtros)
    ] + list(plan.tiene)
    if plan.desde or plan.hasta:
        filt.append("fecha_emision")
    shown = list(dict.fromkeys(asked[:3] + filt))[:4]
    labels = labels_for(shown, question)
    parts = []
    for r in rows:
        extra = _pairs(r, shown, labels)
        parts.append(r["numero"] + (f" ({extra})" if extra else ""))
    more = f" y {len(numeros) - MAX_LIST} más" if len(numeros) > MAX_LIST else ""
    cits = [
        _cit(r, c)
        for r in rows
        for c in ([c for c in shown if _shown(r, c) is not None] or ["numero"])
    ]
    list_view = _table_view(
        rows,
        shown,
        labels,
        f"Facturas{scope}",
        truncated=f"Se muestran {len(rows)} de {len(numeros)}." if more else None,
    )
    return {
        "ok": True,
        "reason": "sql",
        "view": list_view,
        "answer": f"Facturas{scope}: " + ", ".join(parts) + more + _warning(rows),
        "headline": f"Facturas{scope}:"
        + (f" Se muestran {len(rows)} de {len(numeros)}." if more else ""),
        "elements": [
            {"text": part, "citations": [c for c in cits if c["numero"] == r["numero"]]}
            for part, r in zip(parts, rows)
        ],
        "review": [r["numero"] for r in rows if r.get("cuadra") == "0"],
        "citations": cits,
    }


def check_grounding(result: dict[str, Any]) -> dict[str, Any]:
    """Every citation belongs to the selected invoices and carries a stored value.
    Answer text is written only from those same row values (see _shape)."""
    cits = result.get("citations") or []
    if not result.get("ok"):
        return result
    allowed = set(result.get("selected") or [])
    if any(c["numero"] not in allowed or c.get("valor") in (None, "") for c in cits):
        return _refuse("cita_fuera_de_seleccion")
    view = result.get("view") or {}
    shown = [row["numero"] for row in view.get("rows", [])] + (
        [view["numero"]] if "numero" in view else []
    )
    if any(numero not in allowed for numero in shown):
        return _refuse("cita_fuera_de_seleccion")
    return result


def plan_and_run(
    con: sqlite3.Connection, question: str, chat: Any, trace: dict[str, Any] | None = None
) -> tuple[dict[str, Any] | None, list[Any]]:
    """Returns (result or None for 'documentos', raw plans). One retry on invalid plans."""
    messages = [{"role": "system", "content": PLAN_PROMPT}, {"role": "user", "content": question}]
    raws: list[Any] = []
    for attempt in range(2):
        try:
            raw = chat(messages, PLAN_SCHEMA)
        except (AdapterBusy, AdapterTimeout):
            raise
        except AdapterError as e:  # transport or JSON failure counts as an invalid plan
            raw, errors = None, [f"error del modelo: {e}"]
            plan = None
        else:
            plan, errors = validate_plan(raw)
        raws.append(raw)
        if isinstance(raw, dict) and raw.get("intent") == "documentos":
            return None, raws
        if plan is not None:
            if plan.intent == "documentos":
                return None, raws
            result = execute(con, plan, question, trace)
            return check_grounding(result), raws
        if attempt == 0:
            messages += [
                {"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)},
                {
                    "role": "user",
                    "content": "El plan no es válido: "
                    + "; ".join(errors)
                    + ". Corrígelo y devuelve solo el JSON.",
                },
            ]
    return _refuse("plan_invalido"), raws


def run_plan(con: sqlite3.Connection, raw: dict[str, Any], question: str = "") -> dict[str, Any]:
    """Validate and execute one plan without the LLM (tests, evals)."""
    base: dict[str, Any] = {
        "numero": None,
        "parte": None,
        "campos": [],
        "filtros": [],
        "fecha_desde": None,
        "fecha_hasta": None,
        "tiene": [],
    }
    plan, errors = validate_plan({**base, **raw})
    if plan is None:
        return _refuse("plan_invalido", "; ".join(errors))
    return check_grounding(execute(con, plan, question))
