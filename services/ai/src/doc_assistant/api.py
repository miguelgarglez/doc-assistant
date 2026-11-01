"""HTTP interface to the document and invoice workflows."""

import copy
import json
import logging
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from doc_assistant.application.ingest.jobs import IngestJobs, Progress, Stage
from doc_assistant.application.ports.models import AdapterError
from doc_assistant.application.ports.pdf import PdfPort
from doc_assistant.ask import ask
from doc_assistant.ask_schemas import AskRequest, AskResponse
from doc_assistant.ask_stream import STREAM_SCHEMA, queued_ask_stream
from doc_assistant.bootstrap import component_health, lifespan_for
from doc_assistant.ingest import ingest_pdfs, save_and_ingest_pdf
from doc_assistant.invoices import invoice_image, list_invoices, upload_invoice
from doc_assistant.sources import find_source, list_sources, remove_source
from doc_assistant.sources import source_chunks as fetch_source_chunks
from doc_assistant.sources import source_page as fetch_source_page

DEFAULT_CONFIG = Path(__file__).resolve().parents[4] / "config/config.yaml"
ASK_QUEUE_TIMEOUT_S = 60.0


class ErrorBody(BaseModel):
    code: str
    message: str
    reason: str | None = Field(
        default=None,
        description="Upload reason: unsupported_type, size_limit, page_limit, pdf_protected or pdf_unreadable.",
    )
    limit: int | None = Field(
        default=None, description="Upload limit in bytes or pages, according to reason."
    )


class ComponentHealth(BaseModel):
    id: Literal["ai", "llm", "embeddings", "reranker", "ocr", "sqlite"]
    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = None
    detail: str | None = None


class ComponentsHealth(BaseModel):
    components: list[ComponentHealth]


class IngestRequest(BaseModel):
    directory: str = ""


class IngestResponse(BaseModel):
    n_chunks: int
    chunk_ids: list[str]
    warnings: list[str]
    timings: dict[str, float]


class DocumentUploadResponse(BaseModel):
    n_chunks: int
    chunk_ids: list[str]
    warnings: list[str]
    timings: dict[str, float]
    doc_id: str
    path: str
    content_hash: str
    created: bool


class SourceSection(BaseModel):
    section: str
    heading: str | None = None
    pages: list[int]


class SourceChunk(BaseModel):
    chunk_id: str
    section: str
    pages: list[int]
    text: str


class Source(BaseModel):
    id: str
    kind: Literal["pdf", "invoice"]
    name: str
    title: str | None = None
    n_pages: int
    n_chunks: int
    sections: list[SourceSection]
    added_at: str | None = None
    status: Literal["indexed", "review", "no_text"]
    status_detail: str | None = None
    file: str | None = None


class Rect(BaseModel):
    """A rectangle as fractions of the page, origin at the top left."""

    x: float
    y: float
    w: float
    h: float


class PageHighlight(BaseModel):
    """Where a cited quote sits on a page. `reason` says why there are no rectangles."""

    page: int
    found: bool
    reason: Literal["ok", "not_found", "no_positions", "no_file"]
    rects: list[Rect] = Field(default_factory=list)


class IngestStageEvent(BaseModel):
    """One step of an upload being processed (`event: stage`)."""

    stage: Stage
    label: str
    seq: int
    detail: dict[str, Any] = Field(default_factory=dict)


JOB_ID = r"^[A-Za-z0-9_-]{8,64}$"


class Invoice(BaseModel):
    numero: str = Field(min_length=1)
    fecha_emision: str | None = None
    fecha_vencimiento: str | None = None
    emisor: str | None = None
    nif_emisor: str | None = None
    cliente: str | None = None
    nif_cliente: str | None = None
    base_imponible_total: str | None = None
    cuota_iva_total: str | None = None
    irpf_tipo: str | None = None
    irpf_importe: str | None = None
    recargo_total: str | None = None
    importe_total: str | None = None
    iban: str | None = None


class InvoiceListItem(Invoice):
    estado: str
    motivo: str | None = None


class InvoiceUploadResponse(BaseModel):
    record: Invoice
    estado: str
    motivo: str | None = None
    evidencias: dict[str, str | None]
    flags: dict[str, str] = Field(default_factory=dict)
    fichero: str | None = None


def read_upload(file: UploadFile, limit: int) -> bytes | None:
    blocks = []
    size = 0
    while block := file.file.read(min(65536, limit + 1 - size)):
        size += len(block)
        if size > limit:
            return None
        blocks.append(block)
    return b"".join(blocks)


def upload_error(
    code: str, message: str, status: int, *, reason: str | None = None, limit: int | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorBody(code=code, message=message, reason=reason, limit=limit).model_dump(
            exclude_none=True
        ),
    )


def safe_upload_directory(base: Path, name: str) -> bool:
    directory = base / name
    return directory.resolve().is_relative_to(base) and (
        not directory.is_dir()
        or all(child.resolve().is_relative_to(base) for child in directory.iterdir())
    )


def summarize_document(result: Any) -> dict[str, Any]:
    return {
        "kind": "document",
        "doc_id": result["doc_id"],
        "created": result["created"],
        "n_chunks": result["n_chunks"],
    }


def summarize_invoice(result: Any) -> dict[str, Any]:
    return {"kind": "invoice", "numero": result.record.numero, "estado": result.estado}


def tracked(
    jobs: IngestJobs,
    job: str | None,
    run: Callable[[Progress], Any],
    summarize: Callable[[Any], dict[str, Any]],
) -> Any:
    """Run an upload and publish its stages when the client sent a job id."""
    progress = Progress(jobs, job)
    progress("received")
    try:
        result = run(progress)
    except AdapterError as exc:
        if job:
            jobs.fail(job, exc.code, exc.public_message)
        raise
    except Exception:
        logging.getLogger(__name__).exception("Upload processing failed")
        if job:
            jobs.fail(job, "internal_error", "Error interno al procesar el archivo")
        return upload_error("internal_error", "Error interno al procesar el archivo", 500)
    if job:
        if isinstance(result, JSONResponse):
            body = json.loads(bytes(result.body))
            jobs.fail(job, body["code"], body["message"])
        else:
            jobs.done(job, **summarize(result))
    return result


def ingest_event_stream(jobs: IngestJobs, job_id: str) -> Iterator[str]:
    for state in jobs.follow(job_id):
        if state is None:
            yield ": keep-alive\n\n"
            continue
        event = IngestStageEvent(
            stage=state.stage, label=state.label, seq=state.seq, detail=state.detail
        )
        yield f"event: stage\ndata: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"


def create_app(config_path: Path = DEFAULT_CONFIG) -> FastAPI:
    app = FastAPI(title="Doc Assistant AI", version="0.1.0", lifespan=lifespan_for(config_path))
    from doc_assistant.history_api import router as history_router

    app.include_router(history_router)

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            from fastapi.openapi.utils import get_openapi

            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            stream = copy.deepcopy(STREAM_SCHEMA)
            components.update(stream.pop("$defs", {}))
            components["StreamEvent"] = stream
            ingest = IngestStageEvent.model_json_schema(ref_template="#/components/schemas/{model}")
            components.update(ingest.pop("$defs", {}))
            components["IngestStageEvent"] = ingest
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]

    @app.exception_handler(AdapterError)
    async def adapter_error(request: Request, exc: AdapterError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=ErrorBody(code=exc.code, message=exc.public_message).model_dump(),
            headers={"x-request-id": request.state.request_id}
            if hasattr(request.state, "request_id")
            else None,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/components", response_model=ComponentsHealth)
    def health_components(request: Request) -> ComponentsHealth:
        return ComponentsHealth(
            components=[
                ComponentHealth.model_validate(asdict(result))
                for result in component_health(request.app.state.config)
            ]
        )

    @app.post(
        "/ingest",
        response_model=IngestResponse,
        responses={400: {"model": ErrorBody}, 404: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    def ingest(payload: IngestRequest, request: Request) -> Any:
        base = request.app.state.config.data_dir
        relative = Path(payload.directory)
        if relative.is_absolute() or ".." in relative.parts:
            return JSONResponse(
                status_code=400,
                content=ErrorBody(
                    code="invalid_directory", message="Directory must be relative to data_dir"
                ).model_dump(),
            )
        target = (base / relative).resolve()
        if not target.is_relative_to(base) or (
            target.is_dir()
            and any(not child.resolve().is_relative_to(base) for child in target.iterdir())
        ):
            return JSONResponse(
                status_code=400,
                content=ErrorBody(
                    code="invalid_directory", message="Directory contains a path outside data_dir"
                ).model_dump(),
            )
        if not target.is_dir():
            return JSONResponse(
                status_code=404,
                content=ErrorBody(
                    code="directory_not_found", message="Directory does not exist"
                ).model_dump(),
            )
        return ingest_pdfs(config_path, target)

    @app.post(
        "/documents",
        response_model=DocumentUploadResponse,
        responses={400: {"model": ErrorBody}, 413: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    def upload_document(
        file: Annotated[UploadFile, File()],
        request: Request,
        job: Annotated[str | None, Query(pattern=JOB_ID)] = None,
    ) -> Any:
        def run(progress: Progress) -> Any:
            filename = file.filename or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                return upload_error(
                    "invalid_file", "Only PDF uploads are accepted", 400, reason="unsupported_type"
                )
            cfg = request.app.state.config
            if not safe_upload_directory(cfg.data_dir, "documents"):
                return upload_error("invalid_directory", "Upload path escapes data_dir", 400)
            data = read_upload(file, cfg.upload_pdf_max_bytes)
            if data is None:
                return upload_error(
                    "upload_too_large",
                    "PDF exceeds upload limit",
                    413,
                    reason="size_limit",
                    limit=cfg.upload_pdf_max_bytes,
                )
            if not data:
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(code="invalid_file", message="Empty file").model_dump(),
                )
            if not data.startswith(b"%PDF"):
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(
                        code="invalid_file", message="File is not a PDF"
                    ).model_dump(),
                )
            pdf: PdfPort = request.app.state.pdf
            pages, reason = pdf.page_count(data)
            if pages is None:
                return upload_error("invalid_file", "Invalid PDF", 400, reason=reason)
            if pages > cfg.upload_pdf_max_pages:
                return upload_error(
                    "upload_too_large",
                    "PDF exceeds page limit",
                    413,
                    reason="page_limit",
                    limit=cfg.upload_pdf_max_pages,
                )
            return save_and_ingest_pdf(config_path, data, filename, progress=progress)

        return tracked(request.app.state.jobs, job, run, summarize_document)

    @app.post(
        "/ask",
        response_model=AskResponse,
        responses={502: {"model": ErrorBody}, 503: {"model": ErrorBody}},
    )
    def query(payload: AskRequest, request: Request, response: Response) -> Any:
        request_id = str(uuid.uuid4())
        response.headers["x-request-id"] = request_id
        request.state.request_id = request_id
        capacity = request.app.state.ask_capacity
        if not capacity.admitted.acquire(blocking=False):
            error = upload_error(
                "queue_full",
                "Hay demasiadas consultas pendientes. Inténtalo de nuevo en unos segundos.",
                503,
            )
            error.headers["x-request-id"] = request_id
            return error
        acquired = False
        try:
            acquired = capacity.running.acquire(timeout=ASK_QUEUE_TIMEOUT_S)
            if not acquired:
                error = upload_error(
                    "queue_timeout", "La espera ha sido demasiado larga. Inténtalo de nuevo.", 503
                )
                error.headers["x-request-id"] = request_id
                return error
            return ask(config_path, payload.question)
        finally:
            if acquired:
                capacity.running.release()
            capacity.admitted.release()

    @app.post(
        "/ask/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "Server-Sent Events. Each `data:` line is one StreamEvent "
                "(the `event` field is sent as the SSE event name).",
                "content": {
                    "text/event-stream": {"schema": {"$ref": "#/components/schemas/StreamEvent"}}
                },
            }
        },
    )
    def query_stream(payload: AskRequest, request: Request) -> StreamingResponse:
        request_id = str(uuid.uuid4())
        outbox = request.app.state.history_outbox
        stream: Iterator[str] = queued_ask_stream(
            request.app.state.ask_capacity, config_path, payload.question, request_id
        )
        if outbox is not None:
            from doc_assistant.history_stream import outbox_ask_stream

            conversation_id = payload.conversation_id or request_id
            ticket = outbox.ticket(conversation_id)
            stream = outbox_ask_stream(
                request.app.state.ask_capacity,
                config_path,
                payload.question,
                request_id,
                conversation_id,
                outbox,
                ticket=ticket,
            )
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "x-request-id": request_id,
            },
        )

    @app.get("/sources", response_model=list[Source])
    def sources(request: Request) -> Any:
        return list_sources(request.app.state.config)

    @app.get("/sources/{source_id}/chunks", response_model=list[SourceChunk])
    def source_chunks(source_id: str, request: Request) -> Any:
        return [
            SourceChunk.model_validate(row)
            for row in fetch_source_chunks(request.app.state.config, source_id)
        ]

    @app.get(
        "/ingest/jobs/{job_id}/events",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "Server-Sent Events, one `stage` event per step until `done` or "
                "`error`. Follow it with the id sent as `?job=` on the upload.",
                "content": {
                    "text/event-stream": {
                        "schema": {"$ref": "#/components/schemas/IngestStageEvent"}
                    }
                },
            }
        },
    )
    def ingest_events(
        job_id: Annotated[str, PathParam(pattern=JOB_ID)], request: Request
    ) -> StreamingResponse:
        return StreamingResponse(
            ingest_event_stream(request.app.state.jobs, job_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get(
        "/sources/{source_id}/pages/{n}/highlight",
        response_model=PageHighlight,
        responses={404: {"model": ErrorBody}},
    )
    def page_highlight(
        source_id: str,
        n: int,
        quote: Annotated[str, Query(min_length=1, max_length=2000)],
        request: Request,
    ) -> Any:
        cfg = request.app.state.config
        source = find_source(cfg, source_id)
        if source is None:
            return upload_error("source_not_found", "Source does not exist", 404)
        if source["kind"] != "pdf":
            return PageHighlight(page=n, found=False, reason="no_positions")
        path = cfg.data_dir / source["file"] if source["file"] else None
        if path is None or not path.is_file():
            return PageHighlight(page=n, found=False, reason="no_file")
        pdf: PdfPort = request.app.state.pdf
        rects = pdf.locate(path, n, quote)
        if rects is None:
            return PageHighlight(page=n, found=False, reason="not_found")
        return PageHighlight(
            page=n,
            found=True,
            reason="ok",
            rects=[Rect(x=r.x, y=r.y, w=r.w, h=r.h) for r in rects],
        )

    @app.delete("/sources/{source_id}", status_code=204, responses={404: {"model": ErrorBody}})
    def delete_source(source_id: str, request: Request) -> Response:
        cfg = request.app.state.config
        source = find_source(cfg, source_id)
        if source is None:
            return upload_error("source_not_found", "Source does not exist", 404)
        remove_source(cfg, source)
        return Response(status_code=204)

    @app.post(
        "/sources/{source_id}/reindex",
        response_model=IngestResponse,
        responses={400: {"model": ErrorBody}, 404: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    def reindex_source(source_id: str, request: Request) -> Any:
        cfg = request.app.state.config
        source = find_source(cfg, source_id)
        if source is None:
            return upload_error("source_not_found", "Source does not exist", 404)
        if source["kind"] != "pdf" or not source["file"]:
            return upload_error(
                "not_reindexable", "Only stored PDFs can be reindexed; upload invoices again", 400
            )
        return ingest_pdfs(config_path, cfg.data_dir / source["file"])

    @app.get(
        "/sources/{doc_id:path}/pages/{n}",
        responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorBody}},
    )
    def source_page(doc_id: str, n: int, request: Request) -> Response:
        png = fetch_source_page(request.app.state.config, doc_id, n)
        if png is None:
            return JSONResponse(
                status_code=404,
                content=ErrorBody(
                    code="page_not_found", message="Page does not exist"
                ).model_dump(),
            )
        return Response(content=png, media_type="image/png")

    @app.get("/invoices", response_model=list[InvoiceListItem])
    def invoices(request: Request) -> Any:
        return [
            InvoiceListItem.model_validate(
                {**row, "estado": "ok" if row["cuadra"] == "1" else "revisar"}
            )
            for row in list_invoices(request.app.state.config.db)
        ]

    @app.post(
        "/invoices/upload",
        response_model=InvoiceUploadResponse,
        responses={400: {"model": ErrorBody}, 413: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    def invoices_upload(
        file: Annotated[UploadFile, File()],
        request: Request,
        job: Annotated[str | None, Query(pattern=JOB_ID)] = None,
    ) -> Any:
        def run(progress: Progress) -> Any:
            filename = file.filename or "factura.png"
            lower = filename.lower()
            if not lower.endswith((".png", ".jpg", ".jpeg")):
                return upload_error(
                    "invalid_file",
                    "Only PNG/JPG invoice images are accepted",
                    400,
                    reason="unsupported_type",
                )
            cfg = request.app.state.config
            if not safe_upload_directory(cfg.data_dir, "invoices"):
                return upload_error("invalid_directory", "Upload path escapes data_dir", 400)
            data = read_upload(file, cfg.upload_image_max_bytes)
            if data is None:
                return upload_error(
                    "upload_too_large",
                    "Image exceeds upload limit",
                    413,
                    reason="size_limit",
                    limit=cfg.upload_image_max_bytes,
                )
            if not data:
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(code="invalid_file", message="Empty file").model_dump(),
                )
            if not data.startswith((b"\x89PNG", b"\xff\xd8\xff")):
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(
                        code="invalid_file", message="File is not a PNG/JPG image"
                    ).model_dump(),
                )
            result = upload_invoice(config_path, data, filename, progress=progress)
            if not result["record"].get("numero"):
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(
                        code="extraction_failed",
                        message=result.get("motivo") or "Invoice number missing",
                    ).model_dump(),
                )
            return InvoiceUploadResponse(
                record=Invoice.model_validate(result["record"]),
                estado=result["estado"],
                motivo=result.get("motivo"),
                evidencias=result.get("evidencias") or {},
                flags=result.get("flags") or {},
                fichero=result.get("fichero"),
            )

        return tracked(request.app.state.jobs, job, run, summarize_invoice)

    @app.get(
        "/invoices/{invoice_id:path}/image",
        responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorBody}},
    )
    def get_invoice_image(invoice_id: str) -> Response:
        data = invoice_image(config_path, invoice_id)
        if data is None:
            return JSONResponse(
                status_code=404,
                content=ErrorBody(
                    code="invoice_not_found", message="Invoice image not found"
                ).model_dump(),
            )
        media = "image/jpeg" if data.startswith(b"\xff\xd8\xff") else "image/png"
        return Response(content=data, media_type=media)

    return app


app = create_app()
