import pytest
from doubles import FakeLLM
from invoice_battery_support import (
    CASES,
    Case,
    assert_blocks_grounded,
    assert_no_false_answer,
    blocks_of,
    run,
)

from doc_assistant.bootstrap import ask_invoices


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
    from doc_assistant.domain.invoices.fields import FIELD_SPECS

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
