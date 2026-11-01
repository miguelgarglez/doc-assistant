"""PDF rendering and highlighting share one PDFium lock."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock

import pypdfium2

from doc_assistant.infra.pdf.highlight import locate
from doc_assistant.ingest import ingest_pdfs
from doc_assistant.model_fakes import FakeEmbedder


def test_ingest_and_highlight_do_not_enter_pdfium_together(
    config_path: Path, synthetic_pdf: Path, monkeypatch
) -> None:
    original = pypdfium2.PdfDocument
    entered = Event()
    release = Event()
    second_started = Event()
    second_entered = Event()
    guard = Lock()
    calls = 0

    def document(*args, **kwargs):
        nonlocal calls
        with guard:
            calls += 1
            call = calls
        if call == 1:
            entered.set()
            assert release.wait(5)
        else:
            second_entered.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(pypdfium2, "PdfDocument", document)

    def highlight():
        second_started.set()
        return locate(synthetic_pdf, 1, "El robot debe operar a 24 V")

    with ThreadPoolExecutor(max_workers=2) as pool:
        ingest = pool.submit(ingest_pdfs, config_path, synthetic_pdf, embedder=FakeEmbedder())
        try:
            assert entered.wait(5)
            result = pool.submit(highlight)
            assert second_started.wait(5)
            assert not second_entered.wait(0.2)
        finally:
            release.set()
        assert ingest.result(timeout=10)["n_chunks"] > 0
        assert result.result(timeout=10)
        assert second_entered.is_set()
