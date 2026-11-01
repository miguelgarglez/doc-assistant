from collections.abc import Callable
from typing import Any

from doc_assistant.application.invoices.answers import format_answer
from doc_assistant.application.invoices.query import is_invoice_question, plan_and_run
from doc_assistant.application.invoices.upload import upload
from doc_assistant.application.ports.invoice_catalog import InvoiceCatalog
from doc_assistant.application.ports.invoice_writer import InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort


class InvoiceService:
    def __init__(self, catalog: InvoiceCatalog) -> None:
        self.catalog = catalog

    def list_invoices(self) -> list[dict[str, Any]]:
        return self.catalog.rows()

    def image(self, invoice_id: str) -> bytes | None:
        return self.catalog.image(invoice_id)

    def upload(
        self,
        image: bytes,
        filename: str,
        *,
        ocr: OcrPort,
        llm: LLM,
        embedder: Embedder,
        writer_factory: Callable[[Embedder], InvoiceWriter],
        progress: Callable[..., None] | None = None,
    ) -> dict[str, Any]:
        return upload(
            image,
            filename,
            ocr=ocr,
            llm=llm,
            embedder=embedder,
            writer_factory=writer_factory,
            progress=progress,
        )

    def ask(
        self,
        question: str,
        *,
        llm: LLM,
        trace: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self.catalog.open_reader() as reader:
            if not is_invoice_question(question, reader):
                return None
            result, raws = plan_and_run(reader, question, llm.chat, trace)
        return format_answer(result, raws)
