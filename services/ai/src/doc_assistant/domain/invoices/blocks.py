"""Structured blocks for an invoice answer: key data and tables (ADR-014).

The blocks are another rendering of the rows the text was written from, never a second
source. Each cell holds the value as `display_value` shows it, plus the position of the
citation that carries the same stored value. A value the invoice does not have stays empty
(`text` is None) instead of being filled in. The Markdown `answer` keeps saying all of it, so
a client that ignores blocks loses nothing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from doc_assistant.domain.invoices.fields import FIELD_SPECS, display_value

Cite = Callable[[str, str, Any], int | None]

FOLLOW_UP_ORDER = (
    "importe_total",
    "fecha_vencimiento",
    "fecha_emision",
    "emisor",
    "cliente",
    "cuota_iva_total",
    "base_imponible_total",
)
MAX_FOLLOW_UPS = 3


def kind_of(field: str) -> str:
    return "id" if field == "numero" else FIELD_SPECS[field].kind


def _cell(numero: str, field: str, raw: Any, cite: Cite) -> dict[str, Any]:
    if raw in (None, ""):
        return {"text": None, "kind": kind_of(field), "cite": None}
    return {
        "text": display_value(field, raw),
        "kind": kind_of(field),
        "cite": cite(numero, field, raw),
    }


def _note(view: dict[str, Any]) -> str | None:
    review = view.get("review") or []
    if not review:
        return None
    return "Pendiente de revisión: " + ", ".join(review)


def _record(view: dict[str, Any], cite: Cite) -> dict[str, Any]:
    numero = view["numero"]
    items = [
        {
            "field": field,
            "label": view["labels"][field],
            **_cell(numero, field, view["values"].get(field), cite),
        }
        for field in view["fields"]
    ]
    return {
        "type": "key_data",
        "title": view["title"],
        "doc_id": view["doc_id"],
        "items": items,
        "note": _note(view),
    }


def _table(view: dict[str, Any], cite: Cite) -> dict[str, Any]:
    fields = view["fields"]
    rows = [
        {
            "doc_id": row["doc_id"],
            "question": row["question"],
            "cells": [
                _cell(row["numero"], "numero", row["numero"], cite),
                *[_cell(row["numero"], f, row["values"].get(f), cite) for f in fields],
            ],
        }
        for row in view["rows"]
    ]
    columns = [
        {"key": "numero", "label": "Factura", "kind": "id"},
        *[{"key": f, "label": view["labels"][f], "kind": kind_of(f)} for f in fields],
    ]
    total = view.get("total")
    note = " ".join(part for part in (view.get("truncated"), _note(view)) if part) or None
    return {
        "type": "table",
        "title": view.get("title"),
        "columns": columns,
        "rows": rows,
        "summary": None
        if total is None
        else {
            "label": total["label"],
            "text": total["text"],
            "kind": "amount",
            "operation": "sum",
            "refs": [row["cells"][-1]["cite"] for row in rows],
        },
        "note": note,
    }


def build_blocks(view: dict[str, Any] | None, cite: Cite) -> list[dict[str, Any]]:
    if not view:
        return []
    if view["kind"] == "record":
        return [_record(view, cite)]
    if view["kind"] == "table" and view["rows"]:
        return [_table(view, cite)]
    return []


def follow_ups(
    view: dict[str, Any] | None, ask: Callable[[list[str], str], str]
) -> list[dict[str, str]]:
    """Questions about the same invoice for fields it has and the answer did not show.
    `ask(fields, numero)` writes the question; the label is the field's own."""
    if not view or view["kind"] != "record":
        return []
    shown = set(view["fields"])
    out: list[dict[str, str]] = []
    for field in FOLLOW_UP_ORDER:
        if field in shown or view["available"].get(field) in (None, ""):
            continue
        spec = FIELD_SPECS[field]
        out.append(
            {
                "label": spec.label[:1].upper() + spec.label[1:],
                "question": ask([field], view["numero"]),
            }
        )
        if len(out) == MAX_FOLLOW_UPS:
            break
    return out
