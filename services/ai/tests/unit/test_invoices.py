from doc_assistant.application.invoices.query import role_cue, validate_plan
from doc_assistant.domain.invoices.fields import FIELD_SPECS


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


def test_plan_with_only_intent_is_valid():
    plan, errors = validate_plan({"intent": "lista"})
    assert plan is not None and not errors


def test_longer_role_cue_wins():
    assert role_cue("¿qué facturas se han emitido a Lucía Martín?") == "cliente"
    assert role_cue("¿qué facturas ha emitido Lucía?") == "emisor"


def test_followup_question_is_built_from_the_fields_asked():
    from doc_assistant.application.invoices.query import FIELDS, followup_question

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
