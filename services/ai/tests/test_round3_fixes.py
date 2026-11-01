from doc_assistant.verifier import verify

CH = {
    "c": "Campo de visión: HFOV 87° x VFOV 58°. Guarda los últimos 5.000 eventos. Carrera de 18 mm a 45 °C."
}


def cit(q):
    return [{"chunk_id": "c", "quote": q}]


def test_degree_followed_by_word():
    assert verify("87°", cit("HFOV 87° x VFOV 58°"), CH).ok


def test_bare_number_with_unit_in_chunk():
    assert verify("5000", cit("Guarda los últimos 5.000 eventos"), CH).ok


def test_unit_change_still_rejected():
    assert not verify("18 m", cit("Carrera de 18 mm a 45 °C"), CH).ok


def test_celsius_kept():
    assert verify("45 °C", cit("Carrera de 18 mm a 45 °C"), CH).ok
    assert not verify("45 °F", cit("Carrera de 18 mm a 45 °C"), CH).ok


def test_absent_number_rejected():
    assert not verify("6000", cit("Guarda los últimos 5.000 eventos"), CH).ok


from doc_assistant.chunking import chunk_invoice


def test_invoice_header_chunk_has_issuer_and_taxid():
    ch = chunk_invoice(
        {"numero": "F-1", "emisor": "ACME S.L.", "nif_emisor": "B123", "importe_total": "10 EUR"}
    )
    head = [c for c in ch if c["section"] == "cabecera"]
    assert head and "ACME S.L." in head[0]["text"] and "B123" in head[0]["text"]


def test_ingest_survives_bad_files(tmp_path, config_path, synthetic_pdf):
    from doc_assistant.ingest import ingest_pdfs
    from doc_assistant.model_fakes import FakeEmbedder

    (tmp_path / "duplicate.pdf").write_bytes(synthetic_pdf.read_bytes())
    (tmp_path / "roto.pdf").write_bytes(b"%PDF-1.4 garbage")
    (tmp_path / "nota.docx").write_text("x")
    result = ingest_pdfs(config_path, tmp_path, embedder=FakeEmbedder())
    warnings = " ".join(result["warnings"])
    assert "roto.pdf" in warnings and "nota.docx" in warnings
    assert "duplicado" in warnings
    assert result["n_chunks"] > 0


def test_question_guard_before_any_model():
    from doc_assistant.ask import ask

    for q, why in (
        ("", "pregunta_vacia"),
        ("   ", "pregunta_vacia"),
        ("x" * 1001, "pregunta_demasiado_larga"),
    ):
        r = ask("no-existe.yaml", q)
        assert r["ok"] is False and r["reason"] == why
