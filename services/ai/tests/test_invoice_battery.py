"""Synthetic invoice battery: the whole /ask path for invoices with the plan the model would
write. Each case states what the answer must contain, what it must not, and the invariants
that make an answer false: an amount not stored in a selected invoice, a raw decimal, a field
nobody asked for, a citation the text does not show.

Set DOC_ASSISTANT_LIVE_LLM=http://127.0.0.1:<port> to run the same questions against a real
llama-server (the plan then comes from the model, so only the invariants are checked)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

from doc_assistant.config import load_config
from doc_assistant.invoice_fields import format_eur
from doc_assistant.invoices import InvoiceDB, ask_invoices
from doc_assistant.model_fakes import FakeLLM
from doc_assistant.model_http import HttpLLM

AMOUNT_FIELDS = (
    "base_imponible_total",
    "cuota_iva_total",
    "irpf_importe",
    "recargo_total",
    "importe_total",
)

INVOICES = [
    {
        "numero": "FAC-2026-0042",
        "emisor": "Lucía Martín Ortega",
        "nif_emisor": "12345678-K",
        "cliente": "Editorial Atlántida, S.L.",
        "nif_cliente": "B-81234567",
        "fecha_emision": "07 marzo 2026",
        "base_imponible_total": "1610.00",
        "cuota_iva_total": "338.10",
        "irpf_tipo": "15",
        "irpf_importe": "241.50",
        "importe_total": "1706.60",
    },
    {
        "numero": "2026/0317",
        "emisor": "DeltaSistemas Ibérica, S.L.",
        "nif_emisor": "B-82345678",
        "cliente": "Cafetería El Plaza, S.C.P.",
        "nif_cliente": "J-03456789",
        "fecha_emision": "14/02/2026",
        "base_imponible_total": "1350.00",
        "cuota_iva_total": "283.50",
        "importe_total": "1633.50",
    },
    {
        "numero": "LM-7",
        "emisor": "Lucía Marín Ruiz",
        "nif_emisor": "23456781-B",
        "cliente": "Editorial Atlántida, S.L.",
        "fecha_emision": "2026-04-02",
        "importe_total": "99.00",
    },
    {
        "numero": "T-100",
        "emisor": "Talleres Sur, S.A.",
        "cliente": "Taller Norte, S.L.",
        "fecha_emision": "2026-01-15",
        "fecha_vencimiento": "2026-02-15",
        "base_imponible_total": "3000.00",
        "cuota_iva_total": "630.00",
        "importe_total": "3630.00",
        "iban": "ES9121000418450200051332",
    },
    {
        "numero": "T-101",
        "emisor": "Talleres Sur, S.A.",
        "cliente": "Editorial Atlántida, S.L.",
        "fecha_emision": "2026-02-20",
        "base_imponible_total": "10716.00",
        "cuota_iva_total": "2592.59",
        "importe_total": "12345.67",
    },
    {
        "numero": "R-5",
        "emisor": "Ana Ruiz Pérez",
        "nif_emisor": "45678912-Z",
        "cliente": "Cafetería El Plaza, S.C.P.",
        "fecha_emision": "2026-03-03",
        "importe_total": "1000000.50",
    },
    {
        "numero": "RV-9",
        "emisor": "Revisiones Rápidas, S.L.",
        "cliente": "Taller Norte, S.L.",
        "fecha_emision": "2026-05-09",
        "importe_total": "50.00",
        "_cuadra": "0",
    },
]


@dataclass
class Case:
    question: str
    plan: dict[str, Any]
    kind: str = "answer"  # answer | clarify | refuse
    want: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()
    live_want: tuple[str, ...] | None = None
    reason: str | None = None
    note: str = field(default="", repr=False)


def value(question: str, numero: str, campos: list[str], **kw: Any) -> Case:
    return Case(question, {"intent": "valor", "numero": numero, "campos": campos}, **kw)


CASES = [
    value(
        "¿Cuál es el precio final de la factura FAC-2026-0042?",
        "FAC-2026-0042",
        ["importe_total"],
        want=("Factura FAC-2026-0042: precio final: 1.706,60 €",),
        forbid=("Lucía", "emisor", "importe total", "1706"),
    ),
    value(
        "importe total de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["importe_total"],
        want=("Factura FAC-2026-0042: importe total: 1.706,60 €",),
        forbid=("Lucía", "emisor"),
    ),
    value(
        "total de la factura 2026/0317",
        "2026/0317",
        ["importe_total"],
        want=("Factura 2026/0317: total: 1.633,50 €",),
        forbid=("importe total", "Delta", "Plaza"),
    ),
    Case(
        "total de la factura de Lucía Martín",
        {"intent": "valor", "parte": "Lucía Martín", "campos": ["importe_total"]},
        want=("Factura FAC-2026-0042: total: 1.706,60 €",),
        forbid=("emisor", "Lucía"),
    ),
    value(
        "total de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["importe_total", "emisor", "cliente"],
        want=("total: 1.706,60 €",),
        forbid=("emisor", "cliente", "Lucía", "Atlántida"),
        note="the model added fields nobody asked for",
    ),
    value(
        "total y emisor de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["importe_total", "emisor"],
        want=("total: 1.706,60 €; emisor: Lucía Martín Ortega",),
        forbid=("cliente",),
    ),
    value(
        "¿Cuánto IVA lleva la factura 2026/0317?",
        "2026/0317",
        ["cuota_iva_total"],
        want=("IVA: 283,50 €",),
        forbid=("cuota de IVA", "total"),
    ),
    value(
        "base imponible e IVA de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["base_imponible_total", "cuota_iva_total"],
        want=("base imponible: 1.610,00 €; IVA: 338,10 €",),
    ),
    value(
        "retención IRPF de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["irpf_tipo", "irpf_importe"],
        want=("retención IRPF: 241,50 €",),
        forbid=("15 %", "tipo"),
    ),
    value(
        "tipo de IRPF de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["irpf_tipo"],
        want=("tipo de IRPF: 15 %",),
        forbid=("€",),
    ),
    value(
        "total de la factura R-5",
        "R-5",
        ["importe_total"],
        want=("total: 1.000.000,50 €",),
    ),
    value(
        "total de la factura T-101",
        "T-101",
        ["importe_total"],
        want=("total: 12.345,67 €",),
    ),
    value(
        "IBAN de la factura T-100",
        "T-100",
        ["iban"],
        want=("IBAN: ES9121000418450200051332",),
        forbid=("€",),
    ),
    value(
        "IBAN de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["iban"],
        kind="refuse",
        reason="campo_ausente:iban",
    ),
    value(
        "total y IBAN de la factura FAC-2026-0042",
        "FAC-2026-0042",
        ["importe_total", "iban"],
        want=("total: 1.706,60 €; sin dato de IBAN",),
    ),
    value(
        "fecha de vencimiento de la factura T-100",
        "T-100",
        ["fecha_vencimiento"],
        want=("fecha de vencimiento: 2026-02-15",),
    ),
    value(
        "datos de la factura FAC-2026-0042",
        "FAC-2026-0042",
        [],
        want=(
            "importe total: 1.706,60 €",
            "fecha de emisión: 07 marzo 2026",
            "emisor: Lucía Martín Ortega",
            "cliente: Editorial Atlántida, S.L.",
        ),
        note="nothing specific asked: the key data",
    ),
    Case(
        "total de las facturas de Talleres Sur",
        {"intent": "valor", "parte": "Talleres Sur", "campos": ["importe_total"]},
        live_want=("Factura T-100: total: 3.630,00 €", "Factura T-101: total: 12.345,67 €"),
        want=(
            "Talleres Sur, S.A. tiene 2 facturas.",
            "Factura T-100: total: 3.630,00 €",
            "Factura T-101: total: 12.345,67 €",
        ),
        forbid=("emisor",),
    ),
    Case(
        "suma del IVA de Talleres Sur",
        {"intent": "sumar", "parte": "Talleres Sur", "campos": ["cuota_iva_total"]},
        want=("Suma de IVA de Talleres Sur, S.A.: 3.222,59 € en 2 facturas",),
        forbid=("EUR",),
    ),
    Case(
        "suma de los importes de Talleres Sur",
        {"intent": "sumar", "parte": "Talleres Sur", "campos": ["importe_total"]},
        want=("15.975,67 € en 2 facturas",),
        forbid=("EUR", "15975"),
    ),
    Case(
        "¿Cuántas facturas ha emitido Talleres Sur?",
        {"intent": "contar", "parte": "Talleres Sur"},
        want=("2 facturas de Talleres Sur, S.A.",),
        forbid=("€", "emisor"),
    ),
    Case(
        "facturas de más de 1000 euros",
        {
            "intent": "lista",
            "filtros": [{"campo": "importe_total", "op": ">", "valor": "1000"}],
        },
        want=(
            "FAC-2026-0042 (importe total: 1.706,60 €)",
            "2026/0317 (importe total: 1.633,50 €)",
            "T-101 (importe total: 12.345,67 €)",
            "R-5 (importe total: 1.000.000,50 €)",
        ),
        forbid=("LM-7", "RV-9", "emisor"),
    ),
    Case(
        "facturas de Talleres Sur",
        {"intent": "lista", "parte": "Talleres Sur"},
        want=("Facturas de Talleres Sur, S.A.:", "- T-100", "- T-101"),
        forbid=("emisor", "€"),
    ),
    Case(
        "facturas de marzo de 2026",
        {"intent": "lista", "fecha_desde": "2026-03-01", "fecha_hasta": "2026-03-31"},
        want=(
            "FAC-2026-0042 (fecha de emisión: 07 marzo 2026)",
            "R-5 (fecha de emisión: 2026-03-03)",
        ),
        forbid=("T-100", "emisor"),
    ),
    Case(
        "facturas con IRPF",
        {"intent": "lista", "tiene": ["irpf_importe"]},
        want=("FAC-2026-0042 (IRPF: 241,50 €)",),
        forbid=("T-100",),
    ),
    Case(
        "¿Cuál es el precio final de la factura?",
        {"intent": "valor", "campos": ["importe_total"]},
        kind="clarify",
        reason="invoice:aclaracion",
        want=("¿Cuál es el precio final de la factura FAC-2026-0042?", "1.706,60 €"),
        forbid=("1706.60", "importe total"),
    ),
    Case(
        "total de Lucía",
        {"intent": "valor", "parte": "Lucía", "campos": ["importe_total"]},
        kind="clarify",
        reason="invoice:parte_ambigua",
        want=("¿Cuál es el total de la factura LM-7?", "99,00 €"),
    ),
    value(
        "total de la factura FAC-9999",
        "FAC-9999",
        ["importe_total"],
        kind="refuse",
        reason="invoice:factura_no_encontrada",
        want=("No hay ninguna factura con número FAC-9999",),
    ),
    Case(
        "total de las facturas de Pedro Gómez",
        {"intent": "valor", "parte": "Pedro Gómez", "campos": ["importe_total"]},
        kind="refuse",
        reason="invoice:parte_no_encontrada",
    ),
    Case(
        "facturas emitidas a Talleres Sur",
        {"intent": "lista", "parte": "Talleres Sur"},
        kind="refuse",
        reason="invoice:parte_rol_distinto",
    ),
    Case(
        "total de Lucai Martn",
        {"intent": "valor", "parte": "Lucai Martn", "campos": ["importe_total"]},
        want=("total: 1.706,60 €",),
        forbid=("99,00",),
    ),
    Case(
        "total de la factura del NIF 45678912 Z",
        {"intent": "valor", "parte": "45678912 Z", "campos": ["importe_total"]},
        want=("Factura R-5: total: 1.000.000,50 €",),
    ),
    value(
        "total de la factura 2026/317",
        "2026/317",
        ["importe_total"],
        want=("Factura 2026/0317: total: 1.633,50 €",),
    ),
    Case(
        "NIF del cliente de la factura FAC-2026-0042",
        {"intent": "valor", "numero": "FAC-2026-0042", "campos": ["nif_cliente"]},
        want=("NIF del cliente: B-81234567",),
        forbid=("12345678-K", "€"),
    ),
    value(
        "total de la factura RV-9",
        "RV-9",
        ["importe_total"],
        want=("total: 50,00 €", "Nota: facturas pendientes de revisión: RV-9"),
    ),
]

MONEY = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2,} €")
RAW_DECIMAL = re.compile(r"(?<![\d.,])\d+\.\d{1,2}(?![\d.])")


@pytest.fixture
def battery_config(config_path):
    db = InvoiceDB(str(load_config(config_path).db))
    try:
        for row in INVOICES:
            row = dict(row)
            cuadra = row.pop("_cuadra", "1")
            db.upsert(row, cuadra=cuadra)
    finally:
        db.con.close()
    return config_path


def stored_amounts() -> set[str]:
    return {
        shown
        for row in INVOICES
        for f in AMOUNT_FIELDS
        if f in row and (shown := format_eur(row[f]))
    }


def assert_no_false_answer(question: str, result: dict[str, Any]) -> None:
    """The invariants that hold for every answer, whoever wrote the plan."""
    text = result["answer"]
    assert not RAW_DECIMAL.search(text), f"raw decimal in {text!r}"
    assert " EUR" not in text, f"EUR instead of the symbol in {text!r}"
    if result["ok"] and result["reason"] != "sql_vacio":
        sums = {m for m in MONEY.findall(text)} - stored_amounts()
        calculated = {
            block["summary"]["text"]
            for block in result.get("blocks", [])
            if block["type"] == "table" and block.get("summary")
        }
        assert sums <= calculated, f"unsupported amounts: {sums - calculated} in {text!r}"
        for citation in result["citations"]:
            if citation["section"] != "numero":
                assert citation["fragment"] in text, f"citation not shown in {text!r}"
        assert_asked_fields_only(question, result)


def assert_blocks_grounded(result: dict[str, Any]) -> None:
    """Blocks are another rendering of the answer: every cell is a value the text states,
    and a cell with a citation shows exactly what that citation quotes."""
    text = result["answer"].replace("\\", "")
    citations = result["citations"]

    def check(cell: dict[str, Any], doc_id: str, field: str | None) -> None:
        if cell["text"] is None:
            assert cell["cite"] is None
            return
        assert cell["text"] in text, f"{cell['text']!r} not in the answer {text!r}"
        if cell["kind"] == "amount":
            assert cell["text"] in stored_amounts() or re.search(r"(?i)\bsuma\b", text)
        assert cell["cite"] is not None
        if cell["cite"] is not None:
            cited = citations[cell["cite"]]
            assert cited["fragment"] == cell["text"]
            assert cited["doc_id"] == doc_id
            if field:
                assert cited["section"] == field

    for block in result.get("blocks") or []:
        if block["type"] == "key_data":
            for item in block["items"]:
                check(item, block["doc_id"], item["field"])
        else:
            width = len(block["columns"])
            for row in block["rows"]:
                assert len(row["cells"]) == width
                assert row["question"]
                for column, cell in zip(block["columns"], row["cells"], strict=True):
                    check(cell, row["doc_id"], None if column["key"] == "numero" else column["key"])
            if block["summary"]:
                assert block["summary"]["text"] in text
                assert block["summary"]["operation"] == "sum"
                assert block["summary"]["refs"] == [
                    row["cells"][-1]["cite"] for row in block["rows"]
                ]

                def amount(text: str) -> Decimal:
                    return Decimal(text.removesuffix(" €").replace(".", "").replace(",", "."))

                assert amount(block["summary"]["text"]) == sum(
                    (amount(citations[ref]["quote"]) for ref in block["summary"]["refs"]),
                    Decimal(0),
                )


def assert_asked_fields_only(question: str, result: dict[str, Any]) -> None:
    from doc_assistant.invoice_fields import asks_for

    q = question.lower()
    for citation in result["citations"]:
        field_name = citation["section"]
        if field_name in ("numero", "emisor", "cliente") or field_name.startswith("nif_"):
            continue
        assert asks_for(field_name, q) or "datos" in q or "más de" in q or "marzo" in q, (
            f"{field_name} cited without being asked in {question!r}"
        )


def run(config_path, case: Case):
    return ask_invoices(config_path, case.question, llm=FakeLLM(case.plan))


@pytest.mark.parametrize("case", CASES, ids=[c.question for c in CASES])
def test_battery(battery_config, case: Case):
    result = run(battery_config, case)
    assert result is not None
    text = result["answer"]
    if case.kind == "answer":
        assert result["ok"], text
    elif case.kind == "clarify":
        assert not result["ok"] and result["clarification"], text
        text += " " + " ".join(
            f"{c['question']} {c['total'] or ''}" for c in result["clarification"]["candidates"]
        )
    else:
        assert not result["ok"] and not result["clarification"], text
    if case.reason:
        assert result["reason"] == case.reason or result["reason"].endswith(case.reason)
    for piece in case.want:
        assert piece in text, f"{piece!r} not in {text!r}"
    for piece in case.forbid:
        assert piece not in text, f"{piece!r} found in {text!r}"
    assert_no_false_answer(case.question, result)
    assert_blocks_grounded(result)


def test_battery_has_no_false_answer_and_covers_every_intent():
    kinds = {c.kind for c in CASES}
    intents = {c.plan["intent"] for c in CASES}
    assert kinds == {"answer", "clarify", "refuse"}
    assert intents == {"valor", "lista", "contar", "sumar"}
    assert len(CASES) >= 30


LIVE = os.environ.get("DOC_ASSISTANT_LIVE_LLM")


@pytest.mark.skipif(not LIVE, reason="DOC_ASSISTANT_LIVE_LLM not set")
@pytest.mark.parametrize("case", CASES, ids=[c.question for c in CASES])
def test_battery_with_a_real_model(battery_config, case: Case):
    assert LIVE is not None
    llm = HttpLLM(LIVE.rstrip("/") + "/v1/chat/completions", "llm-local", 120)
    result = ask_invoices(battery_config, case.question, llm=llm)
    assert result is not None
    assert_no_false_answer(case.question, result)
    assert_blocks_grounded(result)
    if result["ok"]:
        assert case.kind == "answer", f"answered a {case.kind} case: {result['answer']}"
        for piece in case.want if case.live_want is None else case.live_want:
            assert piece in result["answer"], f"expected {piece!r} in {result['answer']!r}"
        for piece in case.forbid:
            assert piece not in result["answer"], f"{piece!r} in {result['answer']!r}"


# --- structured blocks (ADR-014) ---------------------------------------------------------


def blocks_of(config_path, question: str, plan: dict[str, Any]) -> dict[str, Any]:
    result = ask_invoices(config_path, question, llm=FakeLLM(plan))
    assert result is not None and result["ok"]
    assert_blocks_grounded(result)
    return result


def test_a_question_about_one_invoice_gives_its_key_data(battery_config):
    result = blocks_of(
        battery_config,
        "¿Qué datos tiene la factura FAC-2026-0042?",
        {"intent": "valor", "numero": "FAC-2026-0042", "campos": []},
    )
    (block,) = result["blocks"]
    assert block["type"] == "key_data" and block["title"] == "Datos clave"
    assert [i["field"] for i in block["items"]] == [
        "emisor",
        "cliente",
        "numero",
        "fecha_emision",
        "importe_total",
    ]
    by_field = {i["field"]: i["text"] for i in block["items"]}
    assert by_field["importe_total"] == "1.706,60 €"
    assert by_field["emisor"] == "Lucía Martín Ortega"
    assert all(i["cite"] is not None for i in block["items"])


def test_key_data_keeps_to_the_asked_field(battery_config):
    result = blocks_of(
        battery_config,
        "¿Cuál es el precio final de la factura FAC-2026-0042?",
        {"intent": "valor", "numero": "FAC-2026-0042", "campos": ["importe_total"]},
    )
    (block,) = result["blocks"]
    assert block["title"] == "Factura FAC-2026-0042"
    assert [(i["label"], i["text"]) for i in block["items"]] == [("precio final", "1.706,60 €")]
    assert "Lucía" not in result["answer"]


def test_a_missing_value_stays_empty_instead_of_invented(battery_config):
    result = blocks_of(
        battery_config,
        "¿Qué datos tiene la factura LM-7?",
        {"intent": "valor", "numero": "LM-7", "campos": []},
    )
    (block,) = result["blocks"]
    missing = {i["field"]: i for i in block["items"]}["numero"]
    assert missing["text"] == "LM-7"
    assert all(i["text"] is None and i["cite"] is None for i in block["items"] if i["text"] is None)


def test_key_data_follow_ups_ask_for_fields_the_invoice_has(battery_config):
    result = blocks_of(
        battery_config,
        "¿Cuál es el precio final de la factura T-100?",
        {"intent": "valor", "numero": "T-100", "campos": ["importe_total"]},
    )
    labels = [f["label"] for f in result["follow_ups"]]
    assert labels == ["Fecha de vencimiento", "Fecha de emisión", "Emisor"]
    assert (
        result["follow_ups"][0]["question"]
        == "¿Cuál es la fecha de vencimiento de la factura T-100?"
    )
    assert "Importe total" not in labels


def test_a_list_gives_a_table_with_a_question_per_row(battery_config):
    result = blocks_of(
        battery_config,
        "facturas de Talleres Sur con su importe",
        {"intent": "lista", "parte": "Talleres Sur", "campos": ["importe_total"]},
    )
    (block,) = result["blocks"]
    assert block["type"] == "table"
    assert [c["key"] for c in block["columns"]] == ["numero", "importe_total"]
    assert len(block["rows"]) == 2
    assert block["rows"][0]["question"].startswith("¿Qué datos tiene la factura ")
    assert block["rows"][0]["cells"][0]["cite"] is not None
    assert result["follow_ups"] == []


def test_a_sum_gives_its_rows_and_the_total(battery_config):
    result = blocks_of(
        battery_config,
        "suma de los importes de Talleres Sur",
        {"intent": "sumar", "parte": "Talleres Sur", "campos": ["importe_total"]},
    )
    (block,) = result["blocks"]
    assert block["summary"]["label"] == "Total"
    assert block["summary"]["text"] in result["answer"]


def test_answers_without_a_table_shape_carry_no_blocks(battery_config):
    result = ask_invoices(
        battery_config,
        "¿Cuántas facturas ha emitido Talleres Sur?",
        llm=FakeLLM({"intent": "contar", "parte": "Talleres Sur"}),
    )
    assert result is not None and result["ok"]
    assert result.get("blocks", []) == []


def test_number_question_does_not_reveal_an_unasked_amount(battery_config):
    result = blocks_of(
        battery_config,
        "¿Cuál es el número de la factura T-100?",
        {"intent": "valor", "numero": "T-100", "campos": ["numero"]},
    )
    assert [item["field"] for item in result["blocks"][0]["items"]] == ["numero"]
    assert "3.630,00" not in result["answer"]


def test_listing_numbers_alone_still_has_a_cited_table(battery_config):
    result = blocks_of(
        battery_config,
        "Lista las facturas de Talleres Sur",
        {"intent": "lista", "parte": "Talleres Sur"},
    )
    assert [column["key"] for column in result["blocks"][0]["columns"]] == ["numero"]


def test_comparison_numbers_are_not_duplicated(battery_config):
    result = blocks_of(
        battery_config,
        "Números de las facturas de Talleres Sur",
        {"intent": "valor", "parte": "Talleres Sur", "campos": ["numero"]},
    )
    assert [column["key"] for column in result["blocks"][0]["columns"]] == ["numero"]


def test_general_key_data_is_stable_even_with_an_overbroad_plan(battery_config):
    from doc_assistant.invoice_fields import FIELD_SPECS

    result = blocks_of(
        battery_config,
        "¿Qué datos tiene la factura T-100?",
        {"intent": "valor", "numero": "T-100", "campos": list(FIELD_SPECS)},
    )
    (block,) = result["blocks"]
    assert block["title"] == "Datos clave"
    assert [item["field"] for item in block["items"]] == [
        "emisor",
        "cliente",
        "numero",
        "fecha_emision",
        "importe_total",
    ]
    assert "IBAN" not in result["answer"]


def test_specific_banking_data_does_not_turn_into_a_general_summary(battery_config):
    result = blocks_of(
        battery_config,
        "¿Qué datos bancarios tiene la factura T-100?",
        {"intent": "valor", "numero": "T-100", "campos": ["iban"]},
    )
    assert [item["field"] for item in result["blocks"][0]["items"]] == ["iban"]
    assert "3.630,00 €" not in result["answer"]


def test_battery_rejects_a_false_calculated_total(battery_config):
    result = blocks_of(
        battery_config,
        "suma de los importes de Talleres Sur",
        {"intent": "sumar", "parte": "Talleres Sur", "campos": ["importe_total"]},
    )
    summary = result["blocks"][0]["summary"]
    result["answer"] = result["answer"].replace(summary["text"], "999.999,99 €")
    summary["text"] = "999.999,99 €"
    with pytest.raises(AssertionError):
        assert_blocks_grounded(result)
