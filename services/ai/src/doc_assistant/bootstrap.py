import asyncio
import logging
import os
import secrets
import threading
import time
from collections.abc import AsyncIterator, Callable, Generator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from doc_assistant.api.routes import register_routes
from doc_assistant.api.settings import ApiSettings
from doc_assistant.application.ask import pipeline
from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.application.ask.dependencies import AskContext, AskSettings
from doc_assistant.application.health import check_components
from doc_assistant.application.ingest.jobs import IngestJobs
from doc_assistant.application.ingest.service import IngestService
from doc_assistant.application.invoices.service import InvoiceService
from doc_assistant.application.ports.health import ProbeResult
from doc_assistant.application.ports.invoice_writer import InvoiceWriter
from doc_assistant.application.ports.models import LLM, Embedder, OcrPort, Reranker
from doc_assistant.application.ports.retrieval import RetrievalIndex
from doc_assistant.application.sources import SourceService
from doc_assistant.config import AppConfig, load_config
from doc_assistant.infra.health.probes import probe_index, probe_llama
from doc_assistant.infra.ingest.files import DataDirectoryPdfFiles, FileIngestReader
from doc_assistant.infra.ingest.sqlite import SqliteIngestWriterFactory
from doc_assistant.infra.invoices.catalog import SqliteInvoiceCatalog
from doc_assistant.infra.invoices.writer import SqliteInvoiceWriter
from doc_assistant.infra.models.http import HttpEmbedder, HttpLLM, HttpReranker, LlamaOCR, OllamaOCR
from doc_assistant.infra.pdf.service import PdfService
from doc_assistant.infra.retrieval.sqlite import SqliteRetrievalIndex
from doc_assistant.infra.sources.sqlite import SqliteSourceRepository


def retrieval_index(db: Path, dim: int) -> RetrievalIndex:
    return SqliteRetrievalIndex(db, dim)


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


def ingest_service(cfg: AppConfig) -> IngestService:
    return IngestService(
        FileIngestReader(),
        SqliteIngestWriterFactory(cfg.db),
        DataDirectoryPdfFiles(cfg.data_dir),
        cfg.embeddings.dim or 8,
    )


def ingest_pdfs(
    config_path: str | Path,
    pdf_source: str | Path,
    *,
    invoice_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
    image_path: str | Path | None = None,
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    cfg = load_config(config_path)
    if embedder is None:
        embedder, _, _ = build_adapters(cfg)
    _ = image_path
    return ingest_service(cfg).ingest(
        pdf_source,
        started=started,
        invoice_path=invoice_path,
        embedder=embedder,
        progress=progress,
    )


def save_and_ingest_pdf(
    config_path: str | Path,
    data: bytes,
    filename: str,
    *,
    embedder: Embedder | None = None,
    progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    return ingest_service(cfg).save_and_ingest(
        data,
        filename,
        ingest=lambda path: ingest_pdfs(config_path, path, embedder=embedder, progress=progress),
    )


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


def ask_context(config_path: str | Path) -> AskContext:
    cfg = load_config(config_path)
    settings = AskSettings(
        config_sha256=cfg._source_sha256,
        llm_model=cfg.llm.model,
        embedding_model=cfg.embeddings.model,
        reranker_model=cfg.reranker.model,
        ocr_model=cfg.ocr.model,
        embedding_dim=cfg.embeddings.dim or 8,
        top_k=cfg.top_k,
        answer_mode=cfg.answer_mode,
        inline_citations=cfg.inline_citations,
    )
    return AskContext(
        settings=settings,
        sources=lambda: source_service(cfg),
        models=lambda: build_adapters(cfg),
        ask_invoices=lambda question, llm, trace: ask_invoices(
            config_path, question, llm=llm, trace=trace
        ),
        retrieval_index=lambda dim: retrieval_index(cfg.db, dim),
    )


def ask_events(
    config_path: str | Path,
    question: str,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
    stream: bool = False,
    trace: dict[str, Any] | None = None,
) -> Generator[pipeline.Event, None, None]:
    return pipeline.ask_events(
        lambda: ask_context(config_path),
        question,
        embedder=embedder,
        reranker=reranker,
        llm=llm,
        stream=stream,
        trace=trace,
    )


def ask(
    config_path: str | Path,
    question: str,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return pipeline.ask(
        lambda: ask_context(config_path),
        question,
        embedder=embedder,
        reranker=reranker,
        llm=llm,
        trace=trace,
    )


def lifespan_for(config_path: Path) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
        cfg = app.state.config
        app.state.api_settings = ApiSettings(
            data_dir=cfg.data_dir,
            upload_pdf_max_bytes=cfg.upload_pdf_max_bytes,
            upload_pdf_max_pages=cfg.upload_pdf_max_pages,
            upload_image_max_bytes=cfg.upload_image_max_bytes,
        )
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


DEFAULT_CONFIG = Path(__file__).resolve().parents[4] / "config/config.yaml"


def create_app(config_path: Path = DEFAULT_CONFIG) -> FastAPI:
    app = FastAPI(title="Doc Assistant AI", version="0.1.0", lifespan=lifespan_for(config_path))
    register_routes(
        app,
        config_path,
        ask=lambda *args, **kwargs: ask(*args, **kwargs),
        ask_events=lambda *args, **kwargs: ask_events(*args, **kwargs),
        component_health=lambda: component_health(app.state.config),
        ingest_pdfs=lambda *args, **kwargs: ingest_pdfs(*args, **kwargs),
        invoice_image=lambda *args, **kwargs: invoice_image(*args, **kwargs),
        invoice_service=lambda: invoice_service(app.state.config),
        save_and_ingest_pdf=lambda *args, **kwargs: save_and_ingest_pdf(*args, **kwargs),
        source_service=lambda: source_service(app.state.config),
        upload_invoice=lambda *args, **kwargs: upload_invoice(*args, **kwargs),
    )
    return app


app = create_app()
