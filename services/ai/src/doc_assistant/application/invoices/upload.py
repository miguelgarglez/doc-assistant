from collections.abc import Callable
from typing import Any

from doc_assistant.application.invoices.extract import extract_invoice
from doc_assistant.application.ports.invoice_writer import InvoiceWrite, InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort
from doc_assistant.domain.invoices.chunking import chunk_invoice


def upload(
    image: bytes,
    filename: str,
    *,
    ocr: OcrPort,
    llm: LLM,
    embedder: Embedder,
    writer_factory: Callable[[Embedder], InvoiceWriter],
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    extracted = extract_invoice(image, ocr=ocr, llm=llm, on_stage=progress)
    record = extracted["record"]
    numero = record.get("numero")
    if not numero:
        return {
            "record": record,
            "estado": "revisar",
            "motivo": "sin_numero",
            "evidencias": extracted["evidencias"],
            "flags": extracted["flags"],
        }

    if progress:
        progress("indexing")
    chunks = chunk_invoice(record)
    embeddings = embedder.embed([c["text"] for c in chunks]) if chunks else []

    writer = writer_factory(embedder)
    relative = writer.save(
        InvoiceWrite(
            number=numero,
            record=record,
            state=extracted["estado"],
            reason=extracted["motivo"],
            filename=filename,
            image=image,
            chunks=chunks,
            embeddings=embeddings,
        )
    )

    return {
        "record": record,
        "estado": extracted["estado"],
        "motivo": extracted["motivo"],
        "evidencias": extracted["evidencias"],
        "flags": extracted["flags"],
        "fichero": relative,
    }
