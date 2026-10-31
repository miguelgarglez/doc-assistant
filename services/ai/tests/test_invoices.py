from doc_assistant.invoices import InvoiceDB, run_plan


def db():
    d = InvoiceDB()
    d.upsert(
        {
            "numero": "F-1",
            "emisor": "ACME",
            "nif_emisor": "B1",
            "importe_total": "100.00",
            "iban": None,
        }
    )
    d.upsert({"numero": "F-2", "emisor": "Beta", "nif_emisor": "B2", "importe_total": "250.50"})
    return d


P = {"numero": None, "campos": [], "filtro_campo": None, "filtro_op": None, "filtro_valor": None}


def test_multi_field():
    r = run_plan(db(), {**P, "kind": "campos", "numero": "f-1", "campos": ["emisor", "nif_emisor"]})
    assert r["ok"] and "ACME" in r["answer"] and "B1" in r["answer"] and len(r["citations"]) == 2


def test_absent_invoice_and_field_refuse():
    assert not run_plan(db(), {**P, "kind": "campos", "numero": "F-9", "campos": ["emisor"]})["ok"]
    assert not run_plan(db(), {**P, "kind": "campos", "numero": "F-1", "campos": ["iban"]})["ok"]


def test_filter_and_sum():
    r = run_plan(
        db(),
        {
            **P,
            "kind": "filtro",
            "filtro_campo": "importe_total",
            "filtro_op": ">",
            "filtro_valor": "200",
        },
    )
    assert r["answer"] == "Facturas: F-2"
    s = run_plan(db(), {**P, "kind": "sumar", "campos": ["importe_total"]})
    assert "350.50" in s["answer"]


def test_filter_value_braces_and_null_op():
    from doc_assistant.invoices import InvoiceDB, run_plan

    db = InvoiceDB()
    db.upsert({"numero": "A1", "importe_total": "25000.00", "irpf_importe": "10.00"})
    db.upsert({"numero": "A2", "importe_total": "100.00"})
    r = run_plan(
        db,
        {
            "kind": "filtro",
            "filtro_campo": "importe_total",
            "filtro_op": ">",
            "filtro_valor": "{20000}",
        },
    )
    assert r["answer"] == "Facturas: A1"
    r = run_plan(
        db,
        {"kind": "contar", "filtro_campo": "irpf_importe", "filtro_op": ">", "filtro_valor": None},
    )
    assert r["answer"] == "1 facturas"
    r = run_plan(
        db,
        {
            "kind": "filtro",
            "filtro_campo": "importe_total",
            "filtro_op": ">",
            "filtro_valor": "mucho",
        },
    )
    assert r["ok"] is False


def test_router():
    from doc_assistant.invoices import InvoiceDB, is_invoice_question

    db = InvoiceDB()
    db.upsert({"numero": "F-2024-07", "emisor": "Empresa Ejemplo"})
    assert is_invoice_question("¿Total de la F-2024-07?", db)
    assert is_invoice_question("¿Cuánto suma lo de Empresa Ejemplo?", db)
    assert not is_invoice_question(
        "¿Cuánto tarda en pararse todo cuando alguien pulsa la seta?", db
    )
