def test_ingest_survives_bad_files(tmp_path, config_path, synthetic_pdf):
    from doubles import FakeEmbedder

    from doc_assistant.bootstrap import ingest_pdfs

    (tmp_path / "duplicate.pdf").write_bytes(synthetic_pdf.read_bytes())
    (tmp_path / "roto.pdf").write_bytes(b"%PDF-1.4 garbage")
    (tmp_path / "nota.docx").write_text("x")
    result = ingest_pdfs(config_path, tmp_path, embedder=FakeEmbedder())
    warnings = " ".join(result["warnings"])
    assert "roto.pdf" in warnings and "nota.docx" in warnings
    assert "duplicado" in warnings
    assert result["n_chunks"] > 0
