"""Display and wording rules of invoice answers (invoice_fields)."""

import pytest

from doc_assistant.domain.invoices.fields import (
    FIELD_SPECS,
    asks_for,
    display_value,
    format_eur,
    format_percent,
    labels_for,
    noun_phrase,
    prune_unasked,
    term_for,
)


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("1706.60", "1.706,60 €"),
        ("1.706,60 €", "1.706,60 €"),
        ("1,706.60", "1.706,60 €"),
        ("1706,6", "1.706,60 €"),
        ("99", "99,00 €"),
        ("0.5", "0,50 €"),
        ("1000000", "1.000.000,00 €"),
        ("12345.67 EUR", "12.345,67 €"),
        ("-12.3", "-12,30 €"),
        ("12.3456", "12,3456 €"),
    ],
)
def test_amounts_are_spanish_money(raw, shown):
    assert format_eur(raw) == shown


@pytest.mark.parametrize("raw", [None, "", "abc", "12 abc", "1,2,3"])
def test_amount_that_does_not_parse_is_not_invented(raw):
    assert format_eur(raw) is None


@pytest.mark.parametrize(
    ("raw", "shown"), [("15", "15 %"), ("7.5", "7,5 %"), ("21,00", "21 %"), ("15 %", "15 %")]
)
def test_percent(raw, shown):
    assert format_percent(raw) == shown


def test_display_value_formats_by_kind_and_keeps_the_rest_as_stored():
    assert display_value("importe_total", "1706.60") == "1.706,60 €"
    assert display_value("irpf_tipo", "15") == "15 %"
    assert display_value("importe_total", "pendiente") == "pendiente"
    assert display_value("fecha_emision", "07 marzo 2026") == "07 marzo 2026"
    assert display_value("emisor", "Lucía 15.5") == "Lucía 15.5"
    assert display_value("iban", "ES91 2100") == "ES91 2100"


@pytest.mark.parametrize(
    ("question", "term"),
    [
        ("¿Cuál es el precio final de la factura F-1?", "precio final"),
        ("importe total de F-1", "importe total"),
        ("¿cuánto es el total?", "total"),
        ("PRECIO FINAL", "precio final"),
        ("el importe a pagar", "importe a pagar"),
        ("¿Cuánto cuesta?", None),
    ],
)
def test_term_follows_the_question(question, term):
    assert term_for("importe_total", question) == term


def test_labels_fall_back_to_the_canonical_label_when_the_term_is_not_unique():
    both = labels_for(["irpf_tipo", "irpf_importe"], "tipo de IRPF e IRPF")
    assert both == {"irpf_tipo": "tipo de IRPF", "irpf_importe": "IRPF"}
    clash = labels_for(["nif_emisor", "nif_cliente"], "NIF")
    assert clash == {"nif_emisor": "NIF del emisor", "nif_cliente": "NIF del cliente"}
    assert labels_for(["importe_total"], "precio final") == {"importe_total": "precio final"}
    assert labels_for(["importe_total"], "¿cuánto cuesta?") == {"importe_total": "importe total"}


def test_noun_phrase_has_the_right_article():
    assert noun_phrase("importe_total", "precio final") == "el precio final"
    assert noun_phrase("importe_total", "") == "el importe total"
    assert noun_phrase("fecha_emision", "fecha") == "la fecha"
    assert noun_phrase("cuota_iva_total", "IVA") == "el IVA"
    assert noun_phrase("cuota_iva_total", "") == "la cuota de IVA"


def test_field_kinds_match_the_typed_columns_of_the_index():
    from doc_assistant.infra.invoices.index import AMOUNT_COLS, DATE_COLS

    typed = {k for k, spec in FIELD_SPECS.items() if spec.kind in ("amount", "percent")}
    assert typed == set(AMOUNT_COLS)
    assert {k for k, spec in FIELD_SPECS.items() if spec.kind == "date"} == set(DATE_COLS)
    assert all(spec.article in {"el", "la"} for spec in FIELD_SPECS.values())


def test_extra_fields_are_dropped_only_with_evidence_of_what_was_asked():
    plan = ["importe_total", "emisor", "cliente"]
    assert prune_unasked(plan, "precio final de la factura F-1") == ["importe_total"]
    assert prune_unasked(plan, "total y emisor de F-1") == ["importe_total", "emisor"]
    assert prune_unasked(plan, "datos de la factura F-1") == plan
    assert prune_unasked(["importe_total", "fecha_emision"], "¿cuánto hay que pagar?") == [
        "importe_total"
    ]


def test_a_role_word_that_names_the_party_does_not_ask_for_the_role_field():
    q = "total de las facturas emitidas por Lucía, emisor de la factura"
    assert not asks_for("emisor", "importe de las facturas del emisor Lucía", party_role="emisor")
    assert asks_for("emisor", "¿quién es el emisor de la factura?", party_role="emisor")
    assert asks_for("emisor", q)


def test_nif_is_asked_by_nif_or_cif():
    assert asks_for("nif_emisor", "NIF de Lucía")
    assert asks_for("nif_cliente", "CIF del cliente")
    assert not asks_for("nif_cliente", "total de Lucía")
