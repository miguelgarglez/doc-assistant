import asyncio
import logging
import os
import secrets
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.application.health import check_components
from doc_assistant.application.ingest.jobs import IngestJobs
from doc_assistant.application.invoices.service import InvoiceService
from doc_assistant.application.ports.health import ProbeResult
from doc_assistant.application.ports.invoice_writer import InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort, Reranker
from doc_assistant.application.sources import SourceService
from doc_assistant.config import AppConfig, load_config
from doc_assistant.infra.health.probes import probe_index, probe_llama
from doc_assistant.infra.invoices.catalog import SqliteInvoiceCatalog
from doc_assistant.infra.invoices.writer import SqliteInvoiceWriter
from doc_assistant.infra.models.http import HttpEmbedder, HttpLLM, HttpReranker, LlamaOCR, OllamaOCR
from doc_assistant.infra.pdf.service import PdfService
from doc_assistant.infra.sources.sqlite import SqliteSourceRepository


def build_ocr(cfg: AppConfig) -> OcrPort:
    runtime = os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", cfg.ocr.runtime)
    if runtime == "ollama":
        return OllamaOCR(cfg.ocr.ollama_url(), cfg.ocr.model, cfg.ocr.timeout_s)
    return LlamaOCR(cfg.ocr.base_url, cfg.ocr.model, cfg.ocr.timeout_s)


def build_adapters(cfg: AppConfig) -> tuple[Embedder, Reranker, LLM]:
    embedder = HttpEmbedder(
        cfg.embeddings.url, cfg.embeddings.model, cfg.embeddings.timeout_s, cfg.embeddings.dim
    )
    reranker = HttpReranker(cfg.reranker.url, cfg.reranker.model, cfg.reranker.timeout_s)
    llm = HttpLLM(cfg.llm.url, cfg.llm.model, cfg.llm.timeout_s)
    return embedder, reranker, llm


def component_health(cfg: AppConfig) -> list[ProbeResult]:
    runtime = os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", cfg.ocr.runtime)
    ocr_url = cfg.ocr.ollama_url() if runtime == "ollama" else cfg.ocr.base_url
    ocr_path = "/api/version" if runtime == "ollama" else "/health"
    return check_components(
        [
            lambda: probe_llama("llm", cfg.llm.base_url),
            lambda: probe_llama("embeddings", cfg.embeddings.base_url),
            lambda: probe_llama("reranker", cfg.reranker.base_url),
            lambda: probe_llama("ocr", ocr_url, ocr_path),
            lambda: probe_index(cfg.db),
        ]
    )


def source_service(cfg: AppConfig) -> SourceService:
    return SourceService(SqliteSourceRepository(cfg.db, cfg.data_dir, cfg.embeddings.dim or 8))


def invoice_service(cfg: AppConfig) -> InvoiceService:
    return InvoiceService(SqliteInvoiceCatalog(cfg.db, cfg.data_dir, cfg.embeddings.dim or 8))


def upload_invoice(
    config_path: str | Path,
    image: bytes,
    filename: str,
    *,
    ocr: OcrPort | None = None,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    if ocr is None:
        ocr = build_ocr(cfg)
    if embedder is None or llm is None:
        default_embedder, _, default_llm = build_adapters(cfg)
        embedder = embedder or default_embedder
        llm = llm or default_llm

    def writer_factory(model: Embedder) -> InvoiceWriter:
        dim = getattr(model, "dim", None) or cfg.embeddings.dim or 8
        return SqliteInvoiceWriter(cfg.db, cfg.data_dir, dim)

    return invoice_service(cfg).upload(
        image,
        filename,
        ocr=ocr,
        llm=llm,
        embedder=embedder,
        writer_factory=writer_factory,
        progress=progress,
    )


def invoice_image(config_path: str | Path, invoice_id: str) -> bytes | None:
    return invoice_service(load_config(config_path)).image(invoice_id)


def ask_invoices(
    config_path: str | Path,
    question: str,
    *,
    llm: LLM,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return invoice_service(load_config(config_path)).ask(question, llm=llm, trace=trace)


def lifespan_for(config_path: Path) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
        app.state.jobs = IngestJobs()
        app.state.pdf = PdfService()
        app.state.ask_capacity = AskCapacity()
        app.state.config.db.parent.mkdir(parents=True, exist_ok=True)
        app.state.history_token = os.environ.get(
            "DOC_ASSISTANT_HISTORY_TOKEN"
        ) or secrets.token_urlsafe(32)
        app.state.history_retention_days = max(
            1, int(os.environ.get("DOC_ASSISTANT_HISTORY_RETENTION_DAYS", "30"))
        )
        app.state.history_store = None
        app.state.history_outbox = None
        app.state.history_initialization_error = None
        purge_task = None
        if os.environ.get("DOC_ASSISTANT_HISTORY_ENABLED", "1") != "0":
            from doc_assistant.application.history.outbox import HistoryOutbox
            from doc_assistant.application.ports.history import HistoryRepository
            from doc_assistant.infra.history.sqlite import HistoryStore

            store_lock = threading.Lock()

            def open_history() -> HistoryRepository:
                with store_lock:
                    store: HistoryRepository | None = app.state.history_store
                    if store is not None:
                        return store
                    try:
                        store = HistoryStore(app.state.config.db.parent / "history.db")
                        cutoff = (
                            datetime.now(UTC) - timedelta(days=app.state.history_retention_days)
                        ).isoformat()
                        store.purge_before(cutoff)
                    except Exception as exc:
                        app.state.history_initialization_error = type(exc).__name__
                        raise
                    app.state.history_store = store
                    app.state.history_initialization_error = None
                    return store

            class RecoveringWriter:
                def record(
                    self,
                    request_id: str,
                    conversation_id: str,
                    created_at: str,
                    trace: dict[str, Any],
                ) -> None:
                    open_history().record(request_id, conversation_id, created_at, trace)

            app.state.history_outbox = HistoryOutbox(RecoveringWriter())
            try:
                await asyncio.to_thread(open_history)
            except Exception:
                logging.getLogger(__name__).exception("History initialization failed")

            async def purge() -> None:
                while True:
                    try:
                        store = await asyncio.to_thread(open_history)
                        cutoff = (
                            datetime.now(UTC) - timedelta(days=app.state.history_retention_days)
                        ).isoformat()
                        await asyncio.to_thread(store.purge_before, cutoff)
                    except Exception:
                        logging.getLogger(__name__).exception("History retention failed")
                        await asyncio.sleep(5)
                    else:
                        await asyncio.sleep(3600)

            purge_task = asyncio.create_task(purge())
        try:
            yield
        finally:
            if purge_task is not None:
                purge_task.cancel()
                try:
                    await purge_task
                except asyncio.CancelledError:
                    pass
            if app.state.history_outbox is not None:
                app.state.history_outbox.close()

    return lifespan
