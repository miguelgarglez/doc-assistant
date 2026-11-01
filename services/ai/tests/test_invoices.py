"""Structured invoice path: plan validation, resolution and answer shape."""

import pytest

from doc_assistant.adapters import AdapterError, FakeLLM
from doc_assistant.invoice_fields import FIELD_SPECS
from doc_assistant.invoice_query import (
    is_invoice_question,
    plan_and_run,
    role_cue,
    run_plan,
    validate_plan,
)
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
    assert r["ok"] and "1.706,60 €" in r["answer"] and nums(r) == ["FAC-2026-0042"]


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
    assert r["ok"] and "1.706,60 €" in r["answer"] and "99,00 €" in r["answer"]
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
    assert r["ok"] and nums(r) == ["FAC-2026-0042"] and "1.706,60 €" in r["answer"]
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
    assert "1.805,60 €" in r["answer"] and nums(r) == ["FAC-2026-0042", "LM-7"]
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


def test_identity_fields_follow_the_selecting_party_unless_a_role_is_named():
    con = make(LUCIA)
    r = run_plan(
        con, {"intent": "valor", "parte": "Lucía", "campos": ["nif_cliente"]}, "NIF de Lucía"
    )
    assert r["ok"] and "12345678-K" in r["answer"] and "B-81234567" not in r["answer"]
    r = run_plan(
        con,
        {"intent": "valor", "parte": "Lucía", "campos": ["nif_cliente"]},
        "NIF del cliente de Lucía",
    )
    assert r["ok"] and "B-81234567" in r["answer"]


def test_plan_with_only_intent_is_valid():
    plan, errors = validate_plan({"intent": "lista"})
    assert plan is not None and not errors


def test_number_without_leading_zeros():
    con = make(LUCIA, TECNO)
    r = run_plan(con, {"intent": "valor", "numero": "FAC-2026-42", "campos": ["importe_total"]})
    assert r["ok"] and nums(r) == ["FAC-2026-0042"]
    r = run_plan(con, {"intent": "valor", "numero": "2026/317", "campos": ["importe_total"]})
    assert r["ok"] and nums(r) == ["2026/0317"]


def test_router_matches_whole_words_and_fuzzy_names():
    con = make(LUCIA, TECNO)
    assert not is_invoice_question("¿Puedo usar la pinza en una zona con atmósfera explosiva?", con)
    assert is_invoice_question("total de Lucai Martn", con)
    assert is_invoice_question("¿Cuánto IVA lleva?", con)


def test_missing_campos_fall_back_to_the_words_of_the_question():
    con = make(LUCIA, TECNO)
    r = run_plan(con, {"intent": "valor", "parte": "Lucía Martín"}, "NIF de Lucía Martín")
    assert r["ok"] and "12345678-K" in r["answer"] and "B96060858" not in r["answer"]


def test_years_come_from_the_question_not_the_model():
    con = make(LUCIA, TECNO)
    plan = {
        "intent": "valor",
        "parte": "12345678 K",
        "fecha_desde": "2025-03-01",
        "fecha_hasta": "2025-03-31",
        "campos": ["importe_total"],
    }
    r = run_plan(con, plan, "total de la factura del NIF 12345678 K de marzo")
    assert r["ok"] and "1.706,60 €" in r["answer"]
    r = run_plan(con, plan, "total de la factura del NIF 12345678 K de marzo de 2025")
    assert not r["ok"]


def test_filters_settle_an_ambiguous_name():
    con = make(LUCIA, OTRA_LUCIA)
    plan = {
        "intent": "valor",
        "parte": "Lucía",
        "campos": ["importe_total"],
        "fecha_desde": "2025-03-07",
        "fecha_hasta": "2025-03-07",
    }
    r = run_plan(con, plan, "total de la factura de Lucía del 7 de marzo")
    assert r["ok"] and "1.706,60 €" in r["answer"] and "99,00 €" not in r["answer"]


def test_longer_role_cue_wins():
    assert role_cue("¿qué facturas se han emitido a Lucía Martín?") == "cliente"
    assert role_cue("¿qué facturas ha emitido Lucía?") == "emisor"


@pytest.mark.parametrize("intent", ["valor", "lista", "contar", "sumar"])
def test_v2_answers_keep_inline_citations_and_valid_markdown(config_path, intent):
    from markup import assert_segments_tile, assert_valid_markdown

    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        db.upsert(LUCIA, cuadra="0")
        db.upsert(TECNO)
        db.upsert(OTRA_LUCIA)
    finally:
        db.con.close()
    result = ask_invoices(
        config_path,
        "facturas emitidas a Atlántida",
        llm=FakeLLM({"intent": intent, "parte": "Atlántida", "campos": ["importe_total", "iban"]}),
    )
    assert result is not None and result["ok"] and result["inline"] == "template"
    assert_valid_markdown(result["answer"])
    assert_segments_tile(result)
    bullets = [s for s in result["segments"] if s["text"].lstrip().startswith("- ")]
    assert len(bullets) == 2
    assert {c["doc"] for c in result["citations"]} == {"FAC-2026-0042", "LM-7"}
    for segment in bullets:
        assert segment["refs"]
        assert len({result["citations"][i]["doc"] for i in segment["refs"]}) == 1
        for i in segment["refs"]:
            citation = result["citations"][i]
            assert citation["doc"] in segment["text"]
            assert citation["fragment"] in segment["text"]
    assert result["segments"][-1]["text"].startswith("\n\nNota:")
    if intent == "valor":
        assert "sin dato de IBAN" in result["answer"]
    if intent == "sumar":
        assert "1.805,60 € en 2 facturas" in result["answer"]


def test_v2_value_escapes_data_and_retains_clarification(config_path):
    from markup import assert_segments_tile, assert_valid_markdown

    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        db.upsert({**LUCIA, "numero": "4. [F]*_1", "emisor": "Nombre [literal]*"})
        db.upsert(TECNO)
    finally:
        db.con.close()
    result = ask_invoices(
        config_path,
        "total de factura 4. [F]*_1",
        llm=FakeLLM({"intent": "valor", "numero": "4. [F]*_1", "campos": ["importe_total"]}),
    )
    assert result is not None and result["ok"] and "1.706,60 €" in result["answer"]
    assert "\\[F\\]\\*\\_1" in result["answer"]
    assert_valid_markdown(result["answer"])
    assert_segments_tile(result)
    ambiguous = ask_invoices(
        config_path,
        "¿cuál es el total de la factura?",
        llm=FakeLLM({"intent": "valor", "campos": ["importe_total"]}),
    )
    assert ambiguous is not None and not ambiguous["ok"]
    assert ambiguous["reason"] == "invoice:aclaracion"
    assert "¿Te refieres" in ambiguous["answer"]
    assert ambiguous["citations"] == [] and ambiguous["suggestions"] == []
    clarification = ambiguous["clarification"]
    assert clarification["prompt"] == "¿De qué factura?" and clarification["total"] == 2
    assert {c["doc"] for c in clarification["candidates"]} == {"4. [F]*_1", "2026/0317"}


def test_v2_list_keeps_truncation_visible(config_path):
    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        for i in range(23):
            db.upsert({**LUCIA, "numero": f"F-{i:04}"})
    finally:
        db.con.close()
    result = ask_invoices(config_path, "lista facturas", llm=FakeLLM({"intent": "lista"}))
    assert result is not None and result["ok"]
    assert "Se muestran 20 de 23" in result["answer"]
    assert len(result["citations"]) == 20


def test_v2_list_with_missing_fields_still_cites_each_invoice(config_path):
    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        db.upsert({"numero": "F-1", "importe_total": "10.00"})
    finally:
        db.con.close()
    result = ask_invoices(
        config_path, "lista facturas con IBAN", llm=FakeLLM({"intent": "lista", "campos": ["iban"]})
    )
    assert result is not None and result["ok"]
    assert [(c["doc"], c["section"]) for c in result["citations"]] == [("F-1", "numero")]
    assert result["segments"][-1]["refs"] == [0]


def clarify(config_path, rows, question, plan):
    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        for row in rows:
            db.upsert(row)
    finally:
        db.con.close()
    result = ask_invoices(config_path, question, llm=FakeLLM(plan))
    assert result is not None and not result["ok"]
    return result


def test_clarification_lists_real_candidates_with_a_disambiguated_question(config_path):
    result = clarify(
        config_path,
        [LUCIA, TECNO],
        "¿cuál es el importe total de la factura?",
        {"intent": "valor", "campos": ["importe_total"]},
    )
    assert result["reason"] == "invoice:aclaracion" and result["suggestions"] == []
    by_doc = {c["doc"]: c for c in result["clarification"]["candidates"]}
    assert by_doc["FAC-2026-0042"] == {
        "doc": "FAC-2026-0042",
        "doc_id": by_doc["FAC-2026-0042"]["doc_id"],
        "emisor": "Lucía Martín Ortega",
        "cliente": "Editorial Atlántida, S.L.",
        "fecha": "07 marzo 2026",
        "total": "1.706,60 €",
        "question": "¿Cuál es el importe total de la factura FAC-2026-0042?",
    }
    assert by_doc["2026/0317"]["question"] == "¿Cuál es el importe total de la factura 2026/0317?"
    assert by_doc["FAC-2026-0042"]["doc_id"].startswith("inv-")


def test_clarification_never_shows_data_the_invoice_lacks(config_path):
    row = {"numero": "SIN-DATOS", "emisor": "Solo Emisor"}
    result = clarify(
        config_path,
        [row, TECNO],
        "¿cuál es el total de la factura?",
        {"intent": "valor", "campos": ["importe_total"]},
    )
    bare = next(c for c in result["clarification"]["candidates"] if c["doc"] == "SIN-DATOS")
    assert bare["total"] is None and bare["fecha"] is None and bare["cliente"] is None


def test_party_ambiguity_is_a_clarification_with_context(config_path):
    result = clarify(
        config_path,
        [LUCIA, TECNO, OTRA_LUCIA],
        "importe de las facturas de Lucía",
        {"intent": "valor", "parte": "Lucía", "campos": ["importe_total"]},
    )
    clarification = result["clarification"]
    assert result["reason"] == "invoice:parte_ambigua"
    assert "Lucía Martín Ortega" in clarification["detail"]
    assert {c["doc"] for c in clarification["candidates"]} == {"FAC-2026-0042", "LM-7"}


def test_clarification_truncates_to_five_and_counts_all(config_path):
    rows = [{**LUCIA, "numero": f"F-{i:03}"} for i in range(12)]
    result = clarify(config_path, rows, "¿cuál es el total de la factura?", {"intent": "valor"})
    clarification = result["clarification"]
    assert clarification["total"] == 12 and len(clarification["candidates"]) == 5
    assert "y 7 más" in result["answer"]


def test_followup_question_is_built_from_the_fields_asked():
    from doc_assistant.invoice_query import FIELDS, followup_question

    assert set(FIELD_SPECS) == set(FIELDS)
    assert (
        followup_question(["importe_total"], "A-1")
        == "¿Cuál es el importe total de la factura A-1?"
    )
    assert (
        followup_question(["fecha_emision", "importe_total", "iban"], "A-1")
        == "¿Cuáles son la fecha de emisión, el importe total y el IBAN de la factura A-1?"
    )
    assert followup_question([], "A-1") == "¿Qué datos tiene la factura A-1?"


def test_only_ambiguity_is_a_clarification_not_absence(config_path):
    result = clarify(
        config_path,
        [LUCIA],
        "¿cuál es el total de la factura FAC-9999?",
        {"intent": "valor", "numero": "FAC-9999", "campos": ["importe_total"]},
    )
    assert result["reason"] == "invoice:factura_no_encontrada"
    assert result["clarification"] is None


def test_invoice_trace_captures_validated_plan_and_parameterized_selection(config_path):
    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        db.upsert(LUCIA)
        db.upsert(TECNO)
    finally:
        db.con.close()
    trace = {}
    result = ask_invoices(
        config_path,
        "importe de factura FAC-2026-0042",
        llm=FakeLLM({"intent": "valor", "numero": "FAC-2026-0042", "campos": ["importe_total"]}),
        trace=trace,
    )
    assert result is not None and result["ok"]
    assert trace["plan"]["numero"] == "FAC-2026-0042"
    assert "?" in trace["sql"] and "FAC-2026-0042" not in trace["sql"]
    assert trace["params"] == ["FAC-2026-0042"]
    assert [row["numero"] for row in trace["rows"]] == ["FAC-2026-0042"]
    assert "sql" not in result


def test_invoice_trace_records_clarification_candidates(config_path):
    from doc_assistant.config import load_config
    from doc_assistant.invoices import ask_invoices

    db = InvoiceDB(str(load_config(config_path).db))
    try:
        db.upsert(LUCIA)
        db.upsert(TECNO)
    finally:
        db.con.close()
    trace = {}
    result = ask_invoices(
        config_path,
        "¿cuál es el importe total de la factura?",
        llm=FakeLLM({"intent": "valor", "campos": ["importe_total"]}),
        trace=trace,
    )
    assert result is not None and result["clarification"]
    selection = trace["selection"]
    assert selection["stop_reason"] == "aclaracion"
    assert {c["numero"] for c in selection["clarification"]["candidates"]} == {
        "FAC-2026-0042",
        "2026/0317",
    }
    assert {row["numero"] for row in trace["rows"]} == {"2026/0317", "FAC-2026-0042"}
