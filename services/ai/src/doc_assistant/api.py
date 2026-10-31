"""HTTP interface to the document and invoice workflows."""

import copy
import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import pypdfium2 as pdfium
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, TypeAdapter

from doc_assistant.adapters import AdapterError
from doc_assistant.ask import ask, ask_events
from doc_assistant.chunking import invoice_doc_id, pdf_doc_id
from doc_assistant.config import load_config
from doc_assistant.ingest import ingest_pdfs, save_and_ingest_pdf
from doc_assistant.invoices import InvoiceDB, invoice_image, upload_invoice
from doc_assistant.sources import find_source, list_sources, remove_source
from doc_assistant.store import ChunkStore

DEFAULT_CONFIG = Path(__file__).resolve().parents[4] / "config/config.yaml"


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


class AskResponse(BaseModel):
    ok: bool
    answer: str
    citations: list[Citation]
    reason: str
    suggestions: list[Suggestion] = Field(default_factory=list)


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


class RefusalEvent(BaseModel):
    event: Literal["refusal"] = "refusal"
    answer: str
    reason: str
    retract: bool
    suggestions: list[Suggestion] = Field(default_factory=list)


class DoneEvent(AskResponse):
    event: Literal["done"] = "done"
    timings: dict[str, float]


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = Annotated[
    StepEvent | TokenEvent | CitationsEvent | RefusalEvent | DoneEvent | ErrorEvent,
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


def ask_stream_events(config_path: Path, question: str) -> Iterator[str]:
    """Translate pipeline events into the SSE contract (see docs/streaming.md)."""
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
                yield sse(DoneEvent(**response.model_dump(), timings=timings))
    except AdapterError as exc:
        yield sse(ErrorEvent(code="adapter_error", message=str(exc)))
    except Exception:  # noqa: BLE001 - the stream must always end with done or error
        yield sse(ErrorEvent(code="internal_error", message="Error interno al responder"))


STREAM_SCHEMA = TypeAdapter(StreamEvent).json_schema(ref_template="#/components/schemas/{model}")


def create_app(config_path: Path = DEFAULT_CONFIG) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
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
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]

    @app.exception_handler(AdapterError)
    async def adapter_error(request: Request, exc: AdapterError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content=ErrorBody(code="adapter_error", message=str(exc)).model_dump()
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
    def upload_document(file: Annotated[UploadFile, File()], request: Request) -> Any:
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
                content=ErrorBody(code="invalid_file", message="File is not a PDF").model_dump(),
            )
        try:
            pdf = pdfium.PdfDocument(data)
            try:
                pages = len(pdf)
            finally:
                pdf.close()
        except pdfium.PdfiumError:
            return upload_error("invalid_file", "Invalid PDF", 400)
        if pages > cfg.upload_pdf_max_pages:
            return upload_error("upload_too_large", "PDF exceeds page limit", 413)
        return save_and_ingest_pdf(config_path, data, filename)

    @app.post("/ask", response_model=AskResponse, responses={502: {"model": ErrorBody}})
    def query(payload: AskRequest) -> Any:
        return ask(config_path, payload.question)

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
    def query_stream(payload: AskRequest) -> StreamingResponse:
        return StreamingResponse(
            ask_stream_events(config_path, payload.question),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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
    def invoices_upload(file: Annotated[UploadFile, File()], request: Request) -> Any:
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
        result = upload_invoice(config_path, data, filename)
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
