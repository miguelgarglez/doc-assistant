# Servicio de IA: handoff

Paquete `doc_assistant` en `src/`, Python 3.12 o superior, gestionado con uv. Se migraron adaptadores, fragmentación, ingesta, facturas, almacenamiento, preguntas y verificador del slice; no se migraron evaluación ni datos reales. El verificador conserva las reglas del original. Los puertos LLM, embeddings, reranker y OCR (`OcrPort`) son Protocols; OCR tiene adaptador Ollama GLM-OCR (`http://127.0.0.1:11434`, modelo `glm-ocr`) usado en la subida de facturas.

La configuración incluye `data_dir` (se crea y valida al arrancar) y `ocr`. `/ingest` solo admite una ruta relativa dentro de `data_dir` (vacía = todo `data_dir`) y rechaza absolutas, `..` y symlinks que salgan, con error tipado 400. `POST /documents` sube un PDF multipart a `data_dir/documents` con nombre saneado, lo ingiere y es idempotente por hash de contenido. La configuración se valida con Pydantic al arrancar y está en `../../config/config.yaml`. Las rutas relativas se resuelven desde ese archivo. Ajusta los endpoints de modelos antes de usar `/ingest`, `/documents`, `/invoices/upload` y `/ask`; los valores incluidos son ejemplos locales. Cada PDF se identifica por el nombre sin extensión: nombres iguales en distintas carpetas representan el mismo documento. La reingesta sustituye sus fragmentos y páginas PNG en SQLite; los ID de fragmentos son deterministas. Un PDF sin texto produce una advertencia y sus páginas siguen disponibles.

Facturas (`POST /invoices/upload`, imagen PNG/JPG): OCR → reglas deterministas (etiqueta + número español, `Decimal`) para importes → LLM solo para campos de texto («copia tal cual»). Puertas: suma (`bases+IVA−IRPF+recargo=total`) e `IVA=Σ base×tipo`; si no cuadra → estado `revisar` con motivo; subtotal derivado marcado `derivado`. Respuesta: record + estado + evidencias por campo. Se guarda en la tabla SQL y se indexa en el mismo índice (doc_id = nº factura, página = imagen). `GET /invoices/{id}/image`. Preguntas de factura vía `is_invoice_question` + plan JSON + `run_plan` integradas en `/ask` con citas (nº + campo + fragmento).

La API ofrece `/health`, `/ingest`, `/documents`, `/ask`, `/sources/{doc_id}/pages/{n}`, `/invoices`, `/invoices/upload` y `/invoices/{id}/image`. La respuesta de preguntas incluye citas verificadas, citas SQL de factura, o un rechazo. La verificación es heurística y no demuestra que la respuesta esté implicada semánticamente por la fuente.

Auditoría de tests del slice: `docs/test-audit.md` (81 casos: 26 migrados, 55 excluidos eval, 0 perdidos). Fixtures sintéticos en `../../evidence/fixtures/` (6 facturas PNG+JSON, 2 PDFs demo; regenerar PDFs con `python evidence/fixtures/make_docs.py`).

Desde `services/ai`:

```sh
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python -m doc_assistant.export_openapi
uv run uvicorn doc_assistant.api:app
```

Última comprobación: 42 tests pasan, Ruff y mypy strict sin errores; OpenAPI generado en `openapi.json`. Starlette emite un aviso de deprecación del transporte httpx de TestClient. Las pruebas emplean PDFs y facturas sintéticos y adaptadores falsos; no prueban servidores de modelos reales. Limitación: las reglas de importes asumen etiquetas regulares (techo optimista PD-8); maquetas nuevas o etiquetas raras pueden ir a `revisar`.
