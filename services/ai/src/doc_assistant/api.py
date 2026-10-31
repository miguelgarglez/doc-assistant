"""HTTP interface to the document and invoice workflows."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from doc_assistant.adapters import AdapterError
from doc_assistant.ask import ask
from doc_assistant.config import load_config
from doc_assistant.ingest import ingest_pdfs, save_and_ingest_pdf
from doc_assistant.invoices import InvoiceDB, invoice_image, upload_invoice
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
    section: str
    pages: list[int]
    fragment: str


class AskResponse(BaseModel):
    ok: bool
    answer: str
    citations: list[Citation]
    reason: str


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


class InvoiceUploadResponse(BaseModel):
    record: Invoice
    estado: str
    motivo: str | None = None
    evidencias: dict[str, str | None]
    flags: dict[str, str] = Field(default_factory=dict)
    fichero: str | None = None


def create_app(config_path: Path = DEFAULT_CONFIG) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
        app.state.config.db.parent.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="Doc Assistant AI", version="0.1.0", lifespan=lifespan)

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
        responses={400: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    async def upload_document(file: Annotated[UploadFile, File()]) -> Any:
        filename = file.filename or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            return JSONResponse(
                status_code=400,
                content=ErrorBody(
                    code="invalid_file", message="Only PDF uploads are accepted"
                ).model_dump(),
            )
        data = await file.read()
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
        return save_and_ingest_pdf(config_path, data, filename)

    @app.post("/ask", response_model=AskResponse, responses={502: {"model": ErrorBody}})
    def query(payload: AskRequest) -> Any:
        return ask(config_path, payload.question)

    @app.get(
        "/sources/{doc_id}/pages/{n}",
        responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorBody}},
    )
    def source_page(doc_id: str, n: int, request: Request) -> Response:
        cfg = request.app.state.config
        store = ChunkStore(cfg.db, cfg.embeddings.dim)
        try:
            png = store.page(doc_id, n)
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

    @app.get("/invoices", response_model=list[Invoice])
    def invoices(request: Request) -> Any:
        db = InvoiceDB(str(request.app.state.config.db))
        try:
            return [
                Invoice.model_validate({k: row.get(k) for k in Invoice.model_fields})
                for row in db.rows()
            ]
        finally:
            db.con.close()

    @app.post("/invoices", response_model=Invoice)
    def put_invoice(payload: Invoice, request: Request) -> Invoice:
        db = InvoiceDB(str(request.app.state.config.db))
        try:
            db.upsert(payload.model_dump())
        finally:
            db.con.close()
        return payload

    @app.post(
        "/invoices/upload",
        response_model=InvoiceUploadResponse,
        responses={400: {"model": ErrorBody}, 502: {"model": ErrorBody}},
    )
    async def invoices_upload(file: Annotated[UploadFile, File()]) -> Any:
        filename = file.filename or "factura.png"
        lower = filename.lower()
        if not lower.endswith((".png", ".jpg", ".jpeg")):
            return JSONResponse(
                status_code=400,
                content=ErrorBody(
                    code="invalid_file", message="Only PNG/JPG invoice images are accepted"
                ).model_dump(),
            )
        data = await file.read()
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
        "/invoices/{invoice_id}/image",
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
