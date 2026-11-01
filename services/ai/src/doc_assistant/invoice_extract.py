"""Extracción de facturas (PD-8 / PD-14): OCR → reglas de importes → LLM de texto → puertas."""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from doc_assistant.adapters import LLM, OcrPort

# Importes en formato español (exigen decimales con coma; evita capturar el "15" de "IRPF 15%").
NUM = r"(-?\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})"
# Tipo con o sin paréntesis y signo: "21%", "(21%)", "(-15%)".
RATE = r"\(?\s*-?(\d+(?:,\d+)?)\s*%\s*\)?"
SEP = r"(?:[ \t]*:[ \t]*|[ \t]+)"

TEXT_FIELDS = (
    "invoice_number",
    "issue_date",
    "due_date",
    "seller_name",
    "seller_tax_id",
    "buyer_name",
    "buyer_tax_id",
    "iban",
)

TEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {k: {"type": ["string", "null"]} for k in TEXT_FIELDS},
    "required": list(TEXT_FIELDS),
}

TEXT_PROMPT = (
    "Copia tal cual los campos de texto de esta factura a partir del OCR. "
    "No conviertas formatos ni calcules importes: el código los obtiene por reglas. "
    "Si un dato no aparece, null."
)

RECORD_MAP = {
    "numero": "invoice_number",
    "fecha_emision": "issue_date",
    "fecha_vencimiento": "due_date",
    "emisor": "seller_name",
    "nif_emisor": "seller_tax_id",
    "cliente": "buyer_name",
    "nif_cliente": "buyer_tax_id",
    "iban": "iban",
}

TOL = Decimal("0.02")


def parse_es_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).replace("€", "").replace("%", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?|[+-]?\d+\.\d+", raw):
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return None


def format_amount(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def _evidence_line(ocr: str, needle: str | None) -> str | None:
    if not needle:
        return None
    for line in ocr.splitlines():
        if needle in line:
            return line.strip()
    return needle if needle in ocr else None


def extract_amounts(ocr: str) -> tuple[dict[str, Any], dict[str, str | None], dict[str, str]]:
    """Importes por etiqueta + número en formato español. Marca subtotal derivado."""
    flags: dict[str, str] = {}
    evidence: dict[str, str | None] = {}

    def first(pat: str) -> tuple[Decimal | None, str | None]:
        match = re.search(pat, ocr, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            return None, None
        return parse_es_decimal(match.group(1)), match.group(0).strip()

    def all_matches(pat: str, group: int = 1) -> list[tuple[Decimal, str]]:
        out: list[tuple[Decimal, str]] = []
        for match in re.finditer(pat, ocr, flags=re.IGNORECASE | re.MULTILINE):
            value = parse_es_decimal(match.group(group))
            if value is not None:
                out.append((value, match.group(0).strip()))
        return out

    bases = all_matches(rf"^Base(?: imponible)?(?: IVA)?\s+{RATE}\s+{NUM}", 2)
    cuotas = all_matches(rf"^IVA\s+{RATE}{SEP}{NUM}", 2)
    breakdown: list[dict[str, str]] = []
    for match in re.finditer(
        rf"^Base(?: imponible)?(?: IVA)?\s+{RATE}\s+{NUM}",
        ocr,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        rate = match.group(1).replace(",", ".")
        base = parse_es_decimal(match.group(2))
        if base is None:
            continue
        rate_pat = re.escape(match.group(1))
        cuota_match = re.search(
            rf"^IVA\s+\(?\s*{rate_pat}\s*%\s*\)?{SEP}{NUM}",
            ocr,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        vat = parse_es_decimal(cuota_match.group(1)) if cuota_match else None
        breakdown.append(
            {
                "rate": rate,
                "base": format_amount(base) or "",
                "vat": format_amount(vat) or "",
            }
        )

    sub, sub_ev = first(rf"^Subtotal{SEP}{NUM}")
    if sub is None:  # "Base imponible 1.000,00 €" sin tipo: es el subtotal
        sub, sub_ev = first(rf"^Base(?: imponible)?{SEP}{NUM}")
    if sub is None and bases:
        sub = sum((b for b, _ in bases), Decimal(0))
        flags["base_imponible_total"] = "derivado"
        sub_ev = bases[0][1] if bases else None
    vat_total = sum((c for c, _ in cuotas), Decimal(0)) if cuotas else None
    vat_ev = cuotas[0][1] if cuotas else None
    if vat_total is None and breakdown:
        vats = [parse_es_decimal(row["vat"]) for row in breakdown if row.get("vat")]
        if vats and all(v is not None for v in vats):
            vat_total = sum((v for v in vats if v is not None), Decimal(0))
            vat_ev = " + ".join(row["vat"] for row in breakdown if row.get("vat"))
            flags["cuota_iva_total"] = "derivado"

    recs = all_matches(rf"^Recargo[^\n]*?\s{NUM}\s*€?$")
    irpfs = all_matches(rf"^(?:Retención\s+)?IRPF[^\n]*?\s{NUM}")
    tot, tot_ev = None, None
    totals = all_matches(rf"^(?:TOTAL(?: FACTURA)?|Importe total|Total a pagar){SEP}{NUM}")
    if totals:
        tot, tot_ev = totals[-1]
    irate_match = re.search(
        rf"^(?:Retención\s+)?IRPF\s+{RATE}", ocr, flags=re.IGNORECASE | re.MULTILINE
    )
    irpf_rate = irate_match.group(1).replace(",", ".") if irate_match else None

    amounts = {
        "subtotal": format_amount(sub),
        "vat_total": format_amount(vat_total),
        "irpf_amount": format_amount(abs(irpfs[0][0])) if irpfs else None,
        "irpf_rate": irpf_rate,
        "re_total": format_amount(sum((r for r, _ in recs), Decimal(0))) if recs else None,
        "total": format_amount(tot),
        "vat_breakdown": breakdown,
    }
    evidence.update(
        {
            "base_imponible_total": sub_ev,
            "cuota_iva_total": vat_ev,
            "irpf_importe": irpfs[0][1] if irpfs else None,
            "irpf_tipo": irate_match.group(0).strip() if irate_match else None,
            "recargo_total": recs[0][1] if recs else None,
            "importe_total": tot_ev,
        }
    )
    return amounts, evidence, flags


def check_gates(amounts: dict[str, Any]) -> tuple[str, str | None]:
    """Puertas: suma (bases+IVA−IRPF+recargo=total) e IVA=Σ base×tipo."""
    sub = parse_es_decimal(amounts.get("subtotal"))
    vat = parse_es_decimal(amounts.get("vat_total"))
    total = parse_es_decimal(amounts.get("total"))
    irpf = parse_es_decimal(amounts.get("irpf_amount")) or Decimal(0)
    recargo = parse_es_decimal(amounts.get("re_total")) or Decimal(0)
    if sub is None or vat is None or total is None:
        return "revisar", "importes_incompletos"
    if abs(sub + vat - irpf + recargo - total) > TOL:
        return "revisar", "suma_no_cuadra"
    breakdown = amounts.get("vat_breakdown") or []
    if breakdown:
        expected = Decimal(0)
        try:
            for row in breakdown:
                base = parse_es_decimal(row.get("base"))
                rate = parse_es_decimal(row.get("rate"))
                if base is None or rate is None:
                    return "revisar", "desglose_iva_incompleto"
                expected += base * rate / Decimal(100)
            if abs(expected - vat) > TOL * max(len(breakdown), 1):
                return "revisar", "iva_no_cuadra"
        except (InvalidOperation, TypeError):
            return "revisar", "desglose_iva_incompleto"
    return "ok", None


def extract_text_fields(ocr: str, llm: LLM) -> tuple[dict[str, str | None], dict[str, str | None]]:
    raw = llm.chat(
        [
            {"role": "system", "content": TEXT_PROMPT},
            {"role": "user", "content": f"Texto OCR de la factura:\n{ocr}"},
        ],
        schema=TEXT_SCHEMA,
    )
    fields: dict[str, str | None] = {}
    evidence: dict[str, str | None] = {}
    for key in TEXT_FIELDS:
        value = raw.get(key)
        if value is None or value == "":
            fields[key] = None
            evidence[key] = None
        else:
            text = str(value).strip()
            evidence[key] = _evidence_line(ocr, text)
            fields[key] = text if evidence[key] else None
            if evidence[key] is None:
                evidence[key] = ""
    return fields, evidence


def to_invoice_record(
    text_fields: dict[str, str | None], amounts: dict[str, Any]
) -> dict[str, str | None]:
    record: dict[str, str | None] = {dst: text_fields.get(src) for dst, src in RECORD_MAP.items()}
    record["base_imponible_total"] = amounts.get("subtotal")
    record["cuota_iva_total"] = amounts.get("vat_total")
    record["irpf_tipo"] = amounts.get("irpf_rate")
    record["irpf_importe"] = amounts.get("irpf_amount")
    record["recargo_total"] = amounts.get("re_total")
    record["importe_total"] = amounts.get("total")
    return record


def extract_invoice(
    image: bytes,
    *,
    ocr: OcrPort,
    llm: LLM,
    on_stage: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Devuelve record, estado, motivo, evidencias, flags y texto OCR."""
    if on_stage:
        on_stage("ocr")
    ocr_text = ocr.extract(image)
    if on_stage:
        on_stage("extracting")
    amounts, amount_evidence, flags = extract_amounts(ocr_text)
    text_fields, text_evidence = extract_text_fields(ocr_text, llm)
    for record_field, source_field in RECORD_MAP.items():
        if text_evidence[source_field] == "":
            flags[record_field] = "sin_evidencia"
            text_evidence[source_field] = None
    record = to_invoice_record(text_fields, amounts)
    estado, motivo = check_gates(amounts)
    evidencias: dict[str, str | None] = {
        record_field: text_evidence.get(src) for record_field, src in RECORD_MAP.items()
    }
    evidencias.update(amount_evidence)
    return {
        "record": record,
        "estado": estado,
        "motivo": motivo,
        "evidencias": evidencias,
        "flags": flags,
        "ocr_text": ocr_text,
        "amounts": amounts,
    }
