"""Closed table of invoice fields: how each one is shown and which words ask for it.

Answers are written from stored values, so every display rule lives here and is applied by
code, never by the model:
- amounts are Spanish money ("1.706,60 €"), the IRPF rate is a percentage ("15 %"), text and
  dates are shown as stored (a date that no rule parsed is not rewritten);
- a field is named with the term the question used ("precio final"), and the canonical label
  only when the question used none;
- fields the question did not ask for are dropped from a plan, when at least one asked field
  is evident in the question."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from doc_assistant.domain.invoices.values import fold, parse_amount

Kind = Literal["text", "date", "amount", "percent"]


@dataclass(frozen=True)
class FieldSpec:
    label: str
    article: str
    kind: Kind
    terms: tuple[str, ...] = ()  # phrases a question may use, shown as the answer's label
    cues: tuple[str, ...] = ()  # extra words that also mean "this field was asked"


FIELD_SPECS: dict[str, FieldSpec] = {
    "numero": FieldSpec("número", "el", "text"),
    "fecha_emision": FieldSpec(
        "fecha de emisión",
        "la",
        "date",
        ("fecha de emisión", "fecha de la factura", "fecha"),
        ("cuando", "emitio", "emision"),
    ),
    "fecha_vencimiento": FieldSpec(
        "fecha de vencimiento",
        "la",
        "date",
        ("fecha de vencimiento", "vencimiento"),
        ("vence", "vencen", "plazo"),
    ),
    "emisor": FieldSpec("emisor", "el", "text", ("emisor", "proveedor"), ("emisora",)),
    "nif_emisor": FieldSpec("NIF del emisor", "el", "text", ("NIF del emisor", "CIF del emisor")),
    "cliente": FieldSpec(
        "cliente", "el", "text", ("cliente", "destinatario", "receptor"), ("receptora",)
    ),
    "nif_cliente": FieldSpec(
        "NIF del cliente", "el", "text", ("NIF del cliente", "CIF del cliente")
    ),
    "base_imponible_total": FieldSpec("base imponible", "la", "amount", ("base imponible", "base")),
    "cuota_iva_total": FieldSpec(
        "cuota de IVA", "la", "amount", ("cuota de IVA", "IVA"), ("impuesto",)
    ),
    "irpf_tipo": FieldSpec("tipo de IRPF", "el", "percent", ("tipo de IRPF", "porcentaje de IRPF")),
    "irpf_importe": FieldSpec(
        "retención IRPF",
        "la",
        "amount",
        ("retención de IRPF", "retención IRPF", "retención", "IRPF"),
        ("retenido",),
    ),
    "recargo_total": FieldSpec(
        "recargo de equivalencia", "el", "amount", ("recargo de equivalencia", "recargo")
    ),
    "importe_total": FieldSpec(
        "importe total",
        "el",
        "amount",
        (
            "precio final",
            "precio total",
            "importe total",
            "importe a pagar",
            "total a pagar",
            "coste total",
            "precio",
            "importe",
            "total",
            "coste",
        ),
        ("cuanto", "pagar", "cobrar", "cuesta", "euros", "vale", "valor"),
    ),
    "iban": FieldSpec(
        "IBAN", "el", "text", ("IBAN", "cuenta bancaria"), ("cuenta", "transferencia")
    ),
}
IDENTITY_NIF = ("nif", "cif")
ROLE_FIELDS = {"emisor", "cliente"}
WHO_WORDS = {"quien", "cual", "nombre"}

MONEY_STEP = Decimal("0.01")


def format_eur(value: object) -> str | None:
    """'1706.60' -> '1.706,60 €'. None when the value is not an amount; never rounds away cents."""
    d = parse_amount(value)
    if d is None:
        return None
    if d.as_tuple().exponent >= -2:  # type: ignore[operator]
        d = d.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    text = f"{abs(d):,f}"
    whole, _, frac = text.partition(".")
    return f"{'-' if d < 0 else ''}{whole.replace(',', '.')},{frac} €"


def format_percent(value: object) -> str | None:
    d = parse_amount(value)
    if d is None:
        return None
    text = f"{d.normalize():f}"
    return f"{text.replace('.', ',')} %"


def display_value(field: str, raw: object) -> str:
    """The stored value as the answer shows it. Anything that does not parse stays as stored."""
    spec = FIELD_SPECS.get(field)
    shown = None
    if spec and spec.kind == "amount":
        shown = format_eur(raw)
    elif spec and spec.kind == "percent":
        shown = format_percent(raw)
    return shown if shown is not None else str(raw)


def _variants(word: str) -> set[str]:
    """A question word and its singular forms: 'totales' also reads as 'total'."""
    out = {word}
    if word.endswith("s") and len(word) > 3:
        out.add(word[:-1])
    if word.endswith("es") and len(word) > 4:
        out.add(word[:-2])
    return out


def _contains(words: list[str], phrase: str) -> bool:
    ph = fold(phrase).split()
    if not ph:
        return False
    return any(
        all(p in _variants(w) for p, w in zip(ph, words[i : i + len(ph)], strict=True))
        for i in range(len(words) - len(ph) + 1)
    )


def term_for(field: str, question: str) -> str | None:
    """The longest phrase of the field that the question uses, as written in the table."""
    spec = FIELD_SPECS.get(field)
    if spec is None:
        return None
    words = fold(question).split()
    hits = [t for t in spec.terms if _contains(words, t)]
    return max(hits, key=lambda t: len(fold(t).split())) if hits else None


def labels_for(fields: list[str], question: str) -> dict[str, str]:
    """Label per field: the question's own term when it names exactly one of the fields."""
    used = {f: term_for(f, question) for f in fields}
    counts: dict[str, int] = {}
    for term in used.values():
        if term:
            counts[fold(term)] = counts.get(fold(term), 0) + 1
    return {
        f: term if term and counts[fold(term)] == 1 else FIELD_SPECS[f].label
        for f, term in used.items()
    }


def noun_phrase(field: str, question: str) -> str:
    """'el precio final', 'la fecha de emisión': article plus the question's term or the label."""
    spec = FIELD_SPECS[field]
    term = term_for(field, question)
    text = term or spec.label
    article = spec.article
    if term and fold(term) == "iva":
        article = "el"
    return f"{article} {text}"


def asks_for(field: str, question: str, *, party_role: str | None = None) -> bool:
    """True when the question shows evidence of asking for this field."""
    spec = FIELD_SPECS.get(field)
    if spec is None:
        return False
    words = fold(question).split()
    wordset = set().union(*map(_variants, words)) if words else set()
    if field in ROLE_FIELDS and party_role == field and not wordset & WHO_WORDS:
        return False  # 'emitida por X': the role word names the party, it does not ask for it
    if any(_contains(words, t) for t in spec.terms) or wordset & set(spec.cues):
        return True
    return field.startswith("nif_") and bool(wordset & set(IDENTITY_NIF))


def prune_unasked(fields: list[str], question: str, *, party_role: str | None = None) -> list[str]:
    """Drops plan fields the question never mentions, but only when at least one asked field is
    evident. With no evidence at all the plan stays as the model wrote it."""
    asked = [f for f in fields if asks_for(f, question, party_role=party_role)]
    return asked if asked else fields
