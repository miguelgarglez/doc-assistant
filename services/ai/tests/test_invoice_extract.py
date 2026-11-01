"""Extracción de facturas: reglas, puertas y upload con adaptadores falsos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from doc_assistant.api import create_app
from doc_assistant.ask import ask
from doc_assistant.invoice_extract import check_gates, extract_amounts, extract_invoice
from doc_assistant.model_fakes import FakeEmbedder, FakeLLM, FakeOCR


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


from doc_assistant.infra.invoices.sqlite import InvoiceDB
from doc_assistant.infra.storage.chunks import ChunkStore
from doc_assistant.invoices import upload_invoice

FIXTURES = Path(__file__).resolve().parents[3] / "evidence/fixtures/invoices"


def _es_amount(value: str | float) -> str:
    raw = f"{float(value):.2f}"
    euros, cents = raw.split(".")
    # Spanish thousands optional; rules accept plain 1234,56 too.
    return f"{euros},{cents}"


def ocr_from_ground_truth(gt: dict) -> str:
    lines = [
        f"Factura {gt['invoice_number']}",
        f"Fecha: {gt['issue_date']}",
        f"Vencimiento: {gt['due_date']}",
        f"Emisor: {gt['seller']['name']}",
        f"NIF Emisor: {gt['seller']['tax_id']}",
        f"Cliente: {gt['buyer']['name']}",
        f"NIF Cliente: {gt['buyer']['tax_id']}",
    ]
    for row in gt.get("vat_breakdown") or []:
        rate = str(row["rate"]).replace(".", ",")
        lines.append(f"Base imponible IVA {rate}% {_es_amount(row['base'])}")
        lines.append(f"IVA {rate}% {_es_amount(row['vat'])}")
    if gt.get("subtotal") is not None:
        lines.append(f"Subtotal {_es_amount(gt['subtotal'])}")
    if gt.get("irpf_rate") is not None:
        rate = str(gt["irpf_rate"]).replace(".", ",")
        lines.append(f"IRPF {rate}%")
    if gt.get("irpf_amount") is not None:
        lines.append(f"Retención IRPF {_es_amount(gt['irpf_amount'])}")
    if gt.get("re_total") is not None:
        lines.append(f"Recargo equivalencia {_es_amount(gt['re_total'])}")
    lines.append(f"TOTAL {_es_amount(gt['total'])}")
    if gt.get("iban"):
        lines.append(f"IBAN {gt['iban']}")
    return "\n".join(lines)


def text_llm_from_gt(gt: dict) -> FakeLLM:
    return FakeLLM(
        response={
            "invoice_number": gt["invoice_number"],
            "issue_date": gt["issue_date"],
            "due_date": gt["due_date"],
            "seller_name": gt["seller"]["name"],
            "seller_tax_id": gt["seller"]["tax_id"],
            "buyer_name": gt["buyer"]["name"],
            "buyer_tax_id": gt["buyer"]["tax_id"],
            "iban": gt.get("iban"),
        }
    )


@pytest.mark.parametrize(
    "name",
    ["factura_001", "factura_011", "factura_021", "factura_031", "factura_041", "factura_051"],
)
def test_rules_and_gates_on_synthetic_fixtures(name: str) -> None:
    gt = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["ground_truth"]
    amounts, evidence, flags = extract_amounts(ocr_from_ground_truth(gt))
    assert amounts["total"] == f"{float(gt['total']):.2f}"
    assert amounts["subtotal"] == f"{float(gt['subtotal']):.2f}"
    assert evidence["importe_total"]
    estado, motivo = check_gates(amounts)
    assert estado == "ok", motivo
    assert "base_imponible_total" not in flags


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


def test_extract_invoice_with_fakes() -> None:
    gt = json.loads((FIXTURES / "factura_001.json").read_text(encoding="utf-8"))["ground_truth"]
    result = extract_invoice(
        b"\x89PNG fake",
        ocr=FakeOCR(ocr_from_ground_truth(gt)),
        llm=text_llm_from_gt(gt),
    )
    assert result["estado"] == "ok"
    assert result["record"]["numero"] == "F-2026-001"
    assert result["record"]["emisor"] == gt["seller"]["name"]
    assert result["evidencias"]["importe_total"]


def test_upload_indexes_sql_and_image(config_path: Path) -> None:
    gt = json.loads((FIXTURES / "factura_001.json").read_text(encoding="utf-8"))["ground_truth"]
    png = (FIXTURES / "factura_001.png").read_bytes()
    result = upload_invoice(
        config_path,
        png,
        "factura_001.png",
        ocr=FakeOCR(ocr_from_ground_truth(gt)),
        llm=text_llm_from_gt(gt),
        embedder=FakeEmbedder(dim=8),
    )
    assert result["estado"] == "ok"
    assert result["record"]["numero"] == "F-2026-001"
    from doc_assistant.config import load_config

    cfg = load_config(config_path)
    db = InvoiceDB(str(cfg.db))
    row = db.get("F-2026-001")
    assert row is not None
    assert row["emisor"] == gt["seller"]["name"]
    db.con.close()
    store = ChunkStore(cfg.db, dim=8)
    assert (
        store.page(
            __import__(
                "doc_assistant.domain.documents.ids", fromlist=["invoice_doc_id"]
            ).invoice_doc_id("F-2026-001"),
            1,
        )
        is not None
    )
    assert store.count() > 0
    store.db.close()


def test_api_invoice_upload_and_ask(config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gt = json.loads((FIXTURES / "factura_021.json").read_text(encoding="utf-8"))["ground_truth"]
    png = (FIXTURES / "factura_021.png").read_bytes()
    ocr_text = ocr_from_ground_truth(gt)

    monkeypatch.setattr(
        "doc_assistant.invoices.build_ocr",
        lambda cfg, fake=False, text="": FakeOCR(ocr_text),
    )
    monkeypatch.setattr(
        "doc_assistant.invoices.build_adapters",
        lambda cfg, fake=False: (
            FakeEmbedder(dim=8),
            None,
            text_llm_from_gt(gt),
        ),
    )

    with TestClient(create_app(config_path)) as client:
        response = client.post(
            "/invoices/upload",
            files={"file": ("factura_021.png", png, "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["estado"] == "ok"
        assert body["record"]["numero"] == "A120"
        image = client.get("/invoices/A120/image")
        assert image.status_code == 200
        assert image.content.startswith(b"\x89PNG")

    plan_llm = FakeLLM(
        responses=[
            {
                "intent": "valor",
                "numero": "A120",
                "parte": None,
                "campos": ["importe_total"],
                "filtros": [],
                "fecha_desde": None,
                "fecha_hasta": None,
                "tiene": [],
            }
        ]
    )
    result = ask(
        config_path,
        "¿Cuál es el importe total de la factura A120?",
        embedder=FakeEmbedder(dim=8),
        reranker=__import__("doc_assistant.adapters", fromlist=["FakeReranker"]).FakeReranker(),
        llm=plan_llm,
    )
    assert result["ok"] is True
    assert "23.474,31 €" in result["answer"]
    assert result["citations"][0]["doc"] == "A120"
    assert result["citations"][0]["section"] == "importe_total"
    assert result["citations"][0]["fragment"]


# Formato de pie de factura frecuente: base sin tipo, IVA con el tipo entre paréntesis,
# retención con tipo negativo y "TOTAL A PAGAR"/"TOTAL FACTURA". Importes inventados.
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
