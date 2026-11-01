"""HTTP interface to the document and invoice workflows."""

import copy
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import pypdfium2 as pdfium
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, TypeAdapter

from doc_assistant.adapters import AdapterError
from doc_assistant.ask import ask, ask_events
from doc_assistant.ask_capacity import AskCapacity
from doc_assistant.chunking import invoice_doc_id, pdf_doc_id
from doc_assistant.config import load_config
from doc_assistant.health import ComponentsHealth, check_components
from doc_assistant.highlight import locate
from doc_assistant.ingest import ingest_pdfs, save_and_ingest_pdf
from doc_assistant.ingest_jobs import IngestJobs, Progress, Stage
from doc_assistant.invoices import InvoiceDB, invoice_image, upload_invoice
from doc_assistant.pdf_lock import pdf_lock
from doc_assistant.sources import find_source, list_sources, remove_source
from doc_assistant.store import ChunkStore

DEFAULT_CONFIG = Path(__file__).resolve().parents[4] / "config/config.yaml"
ASK_QUEUE_TIMEOUT_S = 60.0


class ErrorBody(BaseModel):
    code: str
    message: str


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


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    chunk_id: str
    quote: str
    doc: str
    doc_id: str
    section: str
    pages: list[int]
    fragment: str


class Suggestion(BaseModel):
    """A real, nearby source shown when the question cannot be answered."""

    doc: str
    doc_id: str
    section: str
    heading: str | None = None
    pages: list[int]


class Segment(BaseModel):
    """A piece of the answer and the citations that support it.

    `refs` are positions in `citations`. The `text` of all segments concatenates to the answer.
    """

    text: str
    refs: list[int]


class ClarificationCandidate(BaseModel):
    """An invoice the question may refer to. Every field comes from the stored invoice."""

    doc: str
    doc_id: str
    emisor: str | None = None
    cliente: str | None = None
    fecha: str | None = None
    total: str | None = None
    question: str


class Clarification(BaseModel):
    """The question is ambiguous: the user picks one of the real candidates.

    `question` of the chosen candidate is the original question with that invoice named.
    `total` counts every matching invoice; `candidates` holds at most the first five.
    """

    prompt: str
    detail: str | None = None
    total: int
    candidates: list[ClarificationCandidate]


CellKind = Literal["text", "date", "amount", "percent", "id"]


class Cell(BaseModel):
    """One stored value as the answer shows it. `text` is None when the invoice has no such value.

    `cite` is the position in `citations` of the citation that carries the same stored value.
    """

    text: str | None = None
    kind: CellKind
    cite: int | None = None


class KeyDatum(Cell):
    field: str
    label: str


class KeyDataBlock(BaseModel):
    """The data of one invoice, each with its citation."""

    type: Literal["key_data"] = "key_data"
    title: str
    doc_id: str
    items: list[KeyDatum]
    note: str | None = None


class TableColumn(BaseModel):
    key: str
    label: str
    kind: CellKind


class TableRow(BaseModel):
    """`cells` follow `columns`. `question` asks for the data of this row's invoice."""

    doc_id: str
    question: str
    cells: list[Cell]


class TableSummary(BaseModel):
    """Calculated total, with the citation positions of every operand."""

    operation: Literal["sum"] = "sum"
    refs: list[int]
    label: str
    text: str
    kind: Literal["amount"] = "amount"


class TableBlock(BaseModel):
    """Invoices as rows. The first column is the invoice number."""

    type: Literal["table"] = "table"
    title: str | None = None
    columns: list[TableColumn]
    rows: list[TableRow]
    summary: TableSummary | None = None
    note: str | None = None


Block = Annotated[KeyDataBlock | TableBlock, Field(discriminator="type")]


class FollowUp(BaseModel):
    """A question the service can answer from what it found: a field of the same invoice, or a nearby section."""

    label: str
    question: str


class AskResponse(BaseModel):
    ok: bool
    answer: str
    citations: list[Citation]
    segments: list[Segment] = Field(default_factory=list)
    blocks_version: Literal[1] = 1
    blocks: list[Block] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)
    inline: Literal["model", "rules", "template", "none"] = "none"
    reason: str
    suggestions: list[Suggestion] = Field(default_factory=list)
    clarification: Clarification | None = None


StepId = Literal["route", "meta", "invoices", "retrieve", "rerank", "generate", "verify"]


class StepEvent(BaseModel):
    event: Literal["step"] = "step"
    id: StepId
    status: Literal["running", "done"]
    label: str
    data: dict[str, Any] = Field(default_factory=dict)
    elapsed_s: float | None = None


class TokenEvent(BaseModel):
    event: Literal["token"] = "token"
    text: str


class CitationsEvent(BaseModel):
    event: Literal["citations"] = "citations"
    citations: list[Citation]


class BlocksEvent(BaseModel):
    event: Literal["blocks"] = "blocks"
    blocks_version: Literal[1] = 1
    blocks: list[Block]
    follow_ups: list[FollowUp] = Field(default_factory=list)


class RefusalEvent(BaseModel):
    event: Literal["refusal"] = "refusal"
    answer: str
    reason: str
    retract: bool
    suggestions: list[Suggestion] = Field(default_factory=list)


class ClarificationEvent(BaseModel):
    event: Literal["clarification"] = "clarification"
    reason: str
    clarification: Clarification


class DoneEvent(AskResponse):
    event: Literal["done"] = "done"
    timings: dict[str, float]
    request_id: str


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = Annotated[
    StepEvent
    | TokenEvent
    | CitationsEvent
    | BlocksEvent
    | RefusalEvent
    | ClarificationEvent
    | DoneEvent
    | ErrorEvent,
    Field(discriminator="event"),
]


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


def upload_error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=ErrorBody(code=code, message=message).model_dump()
    )


def safe_upload_directory(base: Path, name: str) -> bool:
    directory = base / name
    return directory.resolve().is_relative_to(base) and (
        not directory.is_dir()
        or all(child.resolve().is_relative_to(base) for child in directory.iterdir())
    )


def sse(event: BaseModel) -> str:
    data = event.model_dump(mode="json", exclude={"event"})
    name = event.event  # type: ignore[attr-defined]
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def ask_stream_events(
    config_path: Path, question: str, request_id: str | None = None
) -> Iterator[str]:
    """Translate pipeline events into the SSE contract (see docs/streaming.md)."""
    request_id = request_id or str(uuid.uuid4())
    emitted = False
    try:
        for kind, data in ask_events(config_path, question, stream=True):
            if kind == "step":
                yield sse(StepEvent.model_validate(data))
            elif kind == "token":
                emitted = True
                yield sse(TokenEvent(text=data["text"]))
            else:
                response = AskResponse.model_validate(data)
                if response.ok:
                    yield sse(CitationsEvent(citations=response.citations))
                    if response.blocks or response.follow_ups:
                        yield sse(
                            BlocksEvent(blocks=response.blocks, follow_ups=response.follow_ups)
                        )
                elif response.clarification:
                    yield sse(
                        ClarificationEvent(
                            reason=response.reason, clarification=response.clarification
                        )
                    )
                else:
                    yield sse(
                        RefusalEvent(
                            answer=response.answer,
                            reason=response.reason,
                            retract=emitted,
                            suggestions=response.suggestions,
                        )
                    )
                timings = dict(data.get("latencies") or {})
                timings["total"] = round(sum(timings.values()), 4)
                yield sse(
                    DoneEvent(**response.model_dump(), timings=timings, request_id=request_id)
                )
    except AdapterError as exc:
        yield sse(ErrorEvent(code=exc.code, message=exc.public_message))
    except Exception:  # noqa: BLE001 - the stream must always end with done or error
        yield sse(ErrorEvent(code="internal_error", message="Error interno al responder"))


def queued_ask_stream(
    capacity: AskCapacity, config_path: Path, question: str, request_id: str | None = None
) -> Iterator[str]:
    if not capacity.admitted.acquire(blocking=False):
        yield sse(
            ErrorEvent(
                code="queue_full",
                message="Hay demasiadas consultas pendientes. Inténtalo de nuevo en unos segundos.",
            )
        )
        return
    acquired = False
    try:
        acquired = capacity.running.acquire(blocking=False)
        if not acquired:
            started = time.monotonic()
            yield sse(
                StepEvent(id="route", status="running", label="Esperando turno para responder")
            )
            acquired = capacity.running.acquire(timeout=ASK_QUEUE_TIMEOUT_S)
            if not acquired:
                yield sse(
                    ErrorEvent(
                        code="queue_timeout",
                        message="La espera ha sido demasiado larga. Inténtalo de nuevo.",
                    )
                )
                return
            yield sse(
                StepEvent(
                    id="route",
                    status="done",
                    label="Turno disponible",
                    elapsed_s=round(time.monotonic() - started, 4),
                )
            )
        yield from ask_stream_events(config_path, question, request_id)
    finally:
        if acquired:
            capacity.running.release()
        capacity.admitted.release()


STREAM_SCHEMA = TypeAdapter(StreamEvent).json_schema(ref_template="#/components/schemas/{model}")


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
        if job:
            jobs.fail(job, "internal_error", "Error interno al procesar el archivo")
        raise
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
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
        app.state.jobs = IngestJobs()
        app.state.ask_capacity = AskCapacity()
        app.state.config.db.parent.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="Doc Assistant AI", version="0.1.0", lifespan=lifespan)

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
        return check_components(request.app.state.config)

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
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(
                        code="invalid_file", message="Only PDF uploads are accepted"
                    ).model_dump(),
                )
            cfg = request.app.state.config
            if not safe_upload_directory(cfg.data_dir, "documents"):
                return upload_error("invalid_directory", "Upload path escapes data_dir", 400)
            data = read_upload(file, cfg.upload_pdf_max_bytes)
            if data is None:
                return upload_error("upload_too_large", "PDF exceeds upload limit", 413)
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
            try:
                with pdf_lock:
                    pdf = pdfium.PdfDocument(data)
                    try:
                        pages = len(pdf)
                    finally:
                        pdf.close()
            except pdfium.PdfiumError:
                return upload_error("invalid_file", "Invalid PDF", 400)
            if pages > cfg.upload_pdf_max_pages:
                return upload_error("upload_too_large", "PDF exceeds page limit", 413)
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
        return StreamingResponse(
            queued_ask_stream(
                request.app.state.ask_capacity, config_path, payload.question, request_id
            ),
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
        cfg = request.app.state.config
        store = ChunkStore(cfg.db, cfg.embeddings.dim)
        try:
            return [
                SourceChunk(
                    chunk_id=row["chunk_id"],
                    section=row["section"],
                    pages=json.loads(row["pages"]),
                    text=row["body"],
                )
                for row in store.db.execute(
                    "SELECT chunk_id, section, pages, body FROM chunks WHERE doc = ? ORDER BY rowid",
                    (source_id,),
                )
            ]
        finally:
            store.db.close()

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
        rects = locate(path, n, quote)
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
        cfg = request.app.state.config
        store = ChunkStore(cfg.db, cfg.embeddings.dim)
        try:
            png = store.page(doc_id, n)
            if png is None and not doc_id.startswith(("pdf-", "inv-")):
                matches = [
                    page
                    for key in (pdf_doc_id(doc_id), invoice_doc_id(doc_id))
                    if (page := store.page(key, n)) is not None
                ]
                png = matches[0] if len(matches) == 1 else None
        finally:
            store.db.close()
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
        db = InvoiceDB(str(request.app.state.config.db))
        try:
            return [
                InvoiceListItem.model_validate(
                    {**row, "estado": "ok" if row["cuadra"] == "1" else "revisar"}
                )
                for row in db.rows()
            ]
        finally:
            db.con.close()

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
                return JSONResponse(
                    status_code=400,
                    content=ErrorBody(
                        code="invalid_file", message="Only PNG/JPG invoice images are accepted"
                    ).model_dump(),
                )
            cfg = request.app.state.config
            if not safe_upload_directory(cfg.data_dir, "invoices"):
                return upload_error("invalid_directory", "Upload path escapes data_dir", 400)
            data = read_upload(file, cfg.upload_image_max_bytes)
            if data is None:
                return upload_error("upload_too_large", "Image exceeds upload limit", 413)
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
