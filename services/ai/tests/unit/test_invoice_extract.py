from doc_assistant.application.invoices.extract import check_gates, extract_amounts

PIE_PARENTESIS = """Descripción Cant. Precio IVA Importe
Consultoría 2 500,00 € 21% 1.000,00 €
Base imponible 1.000,00 €
IVA (21%) 210,00 €
Retención IRPF (-15%) -150,00 €
TOTAL A PAGAR 1.060,00 €
"""

PIE_DOS_TIPOS = """Base imponible (21%) 1.000,00 €
IVA (21%) 210,00 €
Base imponible (10%) 200,00 €
IVA (10%) 20,00 €
TOTAL FACTURA 1.430,00 €
Recargo de equivalencia no aplicable.
"""


def test_amount_labels_with_colons_keep_values_and_evidence():
    ocr = "Base imponible: 100,00 EUR\nIVA 21%: 21,00 EUR\nTOTAL: 121,00 EUR"
    amounts, evidence, _ = extract_amounts(ocr)
    assert (amounts["subtotal"], amounts["vat_total"], amounts["total"]) == (
        "100.00",
        "21.00",
        "121.00",
    )
    assert all(
        evidence[field] in ocr
        for field in ("base_imponible_total", "cuota_iva_total", "importe_total")
    )
    assert check_gates(amounts) == ("ok", None)


def test_derived_subtotal_marked_and_sum_gate() -> None:
    ocr = "Base imponible IVA 21% 100,00\nIVA 21% 21,00\nTOTAL 121,00"
    amounts, _evidence, flags = extract_amounts(ocr)
    assert flags.get("base_imponible_total") == "derivado"
    assert amounts["subtotal"] == "100.00"
    assert check_gates(amounts) == ("ok", None)


def test_iva_gate_rejects_incoherent_breakdown() -> None:
    amounts = {
        "subtotal": "100.00",
        "vat_total": "50.00",
        "irpf_amount": None,
        "re_total": None,
        "total": "150.00",
        "vat_breakdown": [{"rate": "21", "base": "100.00", "vat": "50.00"}],
    }
    estado, motivo = check_gates(amounts)
    assert estado == "revisar"
    assert motivo == "iva_no_cuadra"


def test_amounts_with_parenthesised_rates_and_withholding() -> None:
    amounts, _, _ = extract_amounts(PIE_PARENTESIS)
    assert amounts["subtotal"] == "1000.00"
    assert amounts["vat_total"] == "210.00"
    assert amounts["irpf_rate"] == "15"
    assert amounts["irpf_amount"] == "150.00"
    assert amounts["total"] == "1060.00"
    assert check_gates(amounts) == ("ok", None)


def test_amounts_with_two_rates_and_total_factura() -> None:
    amounts, _, flags = extract_amounts(PIE_DOS_TIPOS)
    assert amounts["subtotal"] == "1200.00" and flags["base_imponible_total"] == "derivado"
    assert amounts["vat_total"] == "230.00"
    assert [r["rate"] for r in amounts["vat_breakdown"]] == ["21", "10"]
    assert amounts["re_total"] is None
    assert amounts["total"] == "1430.00"
    assert check_gates(amounts) == ("ok", None)
