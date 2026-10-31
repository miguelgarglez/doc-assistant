"""Structured invoice path: plan validation, resolution and answer shape."""

import pytest

from doc_assistant.adapters import AdapterError, FakeLLM
from doc_assistant.invoice_query import is_invoice_question, plan_and_run, run_plan, validate_plan
from doc_assistant.invoices import InvoiceDB

LUCIA = {
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
}
TECNO = {
    "numero": "2026/0317",
    "emisor": "DeltaSistemas Ibérica, S.L.",
    "nif_emisor": "B-82345678",
    "cliente": "Cafetería El Plaza, S.C.P.",
    "nif_cliente": "J-03456789",
    "fecha_emision": "14/02/2026",
    "base_imponible_total": "1350.00",
    "cuota_iva_total": "283.50",
    "importe_total": "1633.50",
}
OTRA_LUCIA = {
    "numero": "LM-7",
    "emisor": "Lucía Marín Ruiz",
    "nif_emisor": "23456781-B",
    "cliente": "Editorial Atlántida, S.L.",
    "nif_cliente": "B-81234567",
    "fecha_emision": "2026-04-02",
    "importe_total": "99.00",
}


def make(*rows):
    db = InvoiceDB()
    for r in rows:
        db.upsert(r)
    return db.con


def nums(result):
    return sorted({c["numero"] for c in result["citations"]})


@pytest.mark.parametrize(
    "parte",
    [
        "Lucia Martin",
        "Lucía Martín",
        "LUCIA MARTIN ORTEGA",
        "lucia martín ortega",
        "Martín",
        "Lucai Martn",
        "12345678-K",
        "12345678k",
        "12345678 K",
    ],
)
def test_party_variants_resolve_to_one_invoice(parte):
    r = run_plan(
        make(LUCIA, TECNO), {"intent": "valor", "parte": parte, "campos": ["importe_total"]}
    )
    assert r["ok"] and "1706.60" in r["answer"] and nums(r) == ["FAC-2026-0042"]


@pytest.mark.parametrize(
    "numero", ["FAC-2026-0042", "fac 2026 0042", "0042", "2026-0042", "FAC20260042"]
)
def test_number_variants(numero):
    r = run_plan(
        make(LUCIA, TECNO), {"intent": "valor", "numero": numero, "campos": ["importe_total"]}
    )
    assert r["ok"] and nums(r) == ["FAC-2026-0042"]


def test_short_or_wrong_numbers_do_not_match():
    con = make(LUCIA, TECNO)
    assert (
        run_plan(con, {"intent": "valor", "numero": "78", "campos": ["importe_total"]})["ok"]
        is False
    )
    assert (
        run_plan(con, {"intent": "valor", "numero": "078", "campos": ["importe_total"]})["ok"]
        is False
    )
    r = run_plan(con, {"intent": "valor", "numero": "FAC-2026-0999", "campos": ["importe_total"]})
    assert r["reason"] == "factura_no_encontrada"


def test_name_in_numero_slot_is_treated_as_party():
    r = run_plan(
        make(LUCIA, TECNO),
        {"intent": "valor", "numero": "Lucia Martin", "campos": ["importe_total"]},
    )
    assert r["ok"] and nums(r) == ["FAC-2026-0042"]


def test_value_question_never_returns_a_bare_list():
    con = make(LUCIA, TECNO)
    r = run_plan(con, {"intent": "valor", "campos": ["importe_total"]}, "¿cuál es el total?")
    assert (
        not r["ok"]
        and r["reason"] == "aclaracion"
        and set(r["candidates"])
        == {
            "FAC-2026-0042",
            "2026/0317",
        }
    )


def test_two_lucias_ask_for_clarification_and_full_name_disambiguates():
    con = make(LUCIA, TECNO, OTRA_LUCIA)
    r = run_plan(con, {"intent": "valor", "parte": "Lucía", "campos": ["importe_total"]})
    assert r["reason"] == "parte_ambigua" and set(r["candidates"]) == {"FAC-2026-0042", "LM-7"}
    assert "Lucía Martín Ortega" in r["answer"] and "Lucía Marín Ruiz" in r["answer"]
    r = run_plan(con, {"intent": "valor", "parte": "Lucía Martín", "campos": ["importe_total"]})
    assert r["ok"] and nums(r) == ["FAC-2026-0042"]
    r = run_plan(con, {"intent": "valor", "parte": "Lucia Marin", "campos": ["importe_total"]})
    assert r["ok"] and nums(r) == ["LM-7"]


def test_party_with_several_invoices_gets_one_value_per_invoice():
    con = make(LUCIA, TECNO, OTRA_LUCIA)
    r = run_plan(
        con,
        {"intent": "valor", "parte": "Atlántida", "campos": ["importe_total"]},
        "total de las facturas emitidas a Atlántida",
    )
    assert r["ok"] and "1706.60" in r["answer"] and "99.00" in r["answer"]
    assert nums(r) == ["FAC-2026-0042", "LM-7"] and "2026/0317" not in r["answer"]


def test_role_mismatch_is_reported_not_answered():
    con = make(LUCIA, TECNO)
    r = run_plan(
        con,
        {"intent": "valor", "parte": "Lucía", "campos": ["importe_total"]},
        "facturas emitidas a Lucía",
    )
    assert not r["ok"] and r["reason"] == "parte_rol_distinto"


def test_role_picks_the_right_nif():
    r = run_plan(
        make(LUCIA), {"intent": "valor", "parte": "Lucía", "campos": ["nif_emisor", "nif_cliente"]}
    )
    assert r["ok"] and "12345678-K" in r["answer"] and "B-81234567" not in r["answer"]


def test_party_from_question_when_plan_has_none():
    r = run_plan(make(LUCIA, TECNO), {"intent": "valor", "campos": ["iban"]}, "IBAN de Lucía")
    assert r["reason"] == "campo_ausente:iban"
    r = run_plan(
        make(LUCIA, TECNO),
        {"intent": "valor", "campos": ["importe_total"]},
        "¿cuánto hay que pagar a Lucía?",
    )
    assert r["ok"] and nums(r) == ["FAC-2026-0042"]


def test_unknown_party_refuses():
    r = run_plan(
        make(LUCIA, TECNO), {"intent": "valor", "parte": "Pedro Gómez", "campos": ["importe_total"]}
    )
    assert r["reason"] == "parte_no_encontrada" and r["citations"] == []


@pytest.mark.parametrize(
    "valor", ["1650", "1.650", "1650,00", "1.650,00 €", "{1650}", "1650 euros", "1,650.00"]
)
def test_amount_filters_accept_spanish_and_english_formats(valor):
    con = make(LUCIA, TECNO)
    r = run_plan(
        con, {"intent": "lista", "filtros": [{"campo": "importe_total", "op": ">", "valor": valor}]}
    )
    assert r["ok"] and nums(r) == ["FAC-2026-0042"] and "1706.60" in r["answer"]
    r = run_plan(
        con, {"intent": "lista", "filtros": [{"campo": "importe_total", "op": "<", "valor": valor}]}
    )
    assert nums(r) == ["2026/0317"]


def test_dates_month_and_day():
    con = make(LUCIA, TECNO)
    r = run_plan(con, {"intent": "lista", "fecha_desde": "2026-03-01", "fecha_hasta": "2026-03-31"})
    assert nums(r) == ["FAC-2026-0042"]
    r = run_plan(con, {"intent": "lista", "fecha_desde": "marzo de 2026"})
    assert nums(r) == ["FAC-2026-0042"]
    r = run_plan(
        con,
        {
            "intent": "lista",
            "filtros": [{"campo": "fecha_emision", "op": "=", "valor": "14/02/2026"}],
        },
    )
    assert nums(r) == ["2026/0317"]


def test_count_sum_and_has():
    con = make(LUCIA, TECNO, OTRA_LUCIA)
    assert (
        run_plan(con, {"intent": "contar", "parte": "Lucía Martín"})["answer"]
        == "1 factura de Lucía Martín Ortega"
    )
    r = run_plan(con, {"intent": "sumar", "parte": "Atlántida", "campos": ["importe_total"]})
    assert "1805.60" in r["answer"] and nums(r) == ["FAC-2026-0042", "LM-7"]
    r = run_plan(con, {"intent": "lista", "tiene": ["irpf_importe"]})
    assert nums(r) == ["FAC-2026-0042"]


def test_invalid_plans_are_rejected():
    assert validate_plan({"intent": "x"})[0] is None
    base = {
        "intent": "lista",
        "numero": None,
        "parte": None,
        "campos": [],
        "fecha_desde": None,
        "fecha_hasta": None,
        "tiene": [],
    }
    plan, errors = validate_plan(
        {**base, "filtros": [{"campo": "importe_total", "op": ">", "valor": "mucho"}]}
    )
    assert plan is None and errors
    assert validate_plan({**base, "filtros": [], "fecha_desde": "ayer"})[0] is None


def test_one_retry_then_refusal_and_documentos_goes_to_rag():
    con = make(LUCIA, TECNO)
    bad = {
        "intent": "lista",
        "numero": None,
        "parte": None,
        "campos": [],
        "filtros": [{"campo": "importe_total", "op": ">", "valor": "mucho"}],
        "fecha_desde": None,
        "fecha_hasta": None,
        "tiene": [],
    }
    good = {**bad, "filtros": [{"campo": "importe_total", "op": ">", "valor": "1650"}]}
    llm = FakeLLM(responses=[bad, good])
    r, raws = plan_and_run(con, "facturas de más de 1650", llm.chat)
    assert r is not None and r["ok"] and len(raws) == 2
    r, raws = plan_and_run(con, "x", FakeLLM(responses=[bad, bad]).chat)
    assert r is not None and r["reason"] == "plan_invalido" and len(raws) == 2

    def broken(*_a):
        raise AdapterError("timeout")

    r, _ = plan_and_run(con, "x", broken)
    assert r is not None and r["reason"] == "plan_invalido"
    r, _ = plan_and_run(con, "x", FakeLLM({**bad, "intent": "documentos"}).chat)
    assert r is None


def test_router():
    con = make(LUCIA, TECNO)
    assert is_invoice_question("¿Total de la FAC-2026-0042?", con)
    assert is_invoice_question("¿Cuánto hay que pagar a Lucía?", con)
    assert is_invoice_question("¿qué debe Deltasistemas?", con)
    assert is_invoice_question("pagos al 12345678K", con)
    assert not is_invoice_question(
        "¿Cuánto tarda en pararse todo cuando alguien pulsa la seta?", con
    )


def test_citations_only_from_selected_invoices():
    con = make(LUCIA, TECNO, OTRA_LUCIA)
    for plan, q in [
        (
            {
                "intent": "valor",
                "parte": "Lucía Martín",
                "campos": ["importe_total", "cuota_iva_total"],
            },
            "",
        ),
        (
            {
                "intent": "lista",
                "filtros": [{"campo": "importe_total", "op": ">", "valor": "1000"}],
            },
            "",
        ),
        ({"intent": "contar", "parte": "Atlántida"}, "emitidas a Atlántida"),
    ]:
        r = run_plan(con, plan, q)
        assert r["ok"] and set(nums(r)) <= set(r["selected"])
        assert all(c["valor"] not in (None, "") for c in r["citations"])
