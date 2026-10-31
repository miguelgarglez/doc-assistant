# Servicio de IA: handoff

Paquete `doc_assistant` en `src/`, Python 3.12 o superior, gestionado con uv. Se migraron adaptadores, fragmentación, ingesta, facturas, almacenamiento, preguntas y verificador del slice; no se migraron evaluación ni datos reales. El verificador conserva las reglas del original. Los puertos LLM, embeddings, reranker y OCR (`OcrPort`) son Protocols; OCR tiene adaptador Ollama GLM-OCR (`http://127.0.0.1:11434`, modelo `glm-ocr`) usado en la subida de facturas.

La configuración incluye `data_dir` (se crea y valida al arrancar) y `ocr`. `/ingest` solo admite una ruta relativa dentro de `data_dir` (vacía = todo `data_dir`) y rechaza absolutas, `..` y symlinks que salgan, con error tipado 400. `POST /documents` sube un PDF multipart a `data_dir/documents` con nombre saneado, lo ingiere y es idempotente por hash de contenido. La configuración se valida con Pydantic al arrancar y está en `../../config/config.yaml`. Las rutas relativas se resuelven desde ese archivo. Ajusta los endpoints de modelos antes de usar `/ingest`, `/documents`, `/invoices/upload` y `/ask`; los valores incluidos son ejemplos locales. Cada PDF se identifica por el nombre sin extensión: nombres iguales en distintas carpetas representan el mismo documento. La reingesta sustituye sus fragmentos y páginas PNG en SQLite; los ID de fragmentos son deterministas. Un PDF sin texto produce una advertencia y sus páginas siguen disponibles.

Facturas (`POST /invoices/upload`, imagen PNG/JPG): OCR → reglas deterministas (etiqueta + número español, `Decimal`) para importes → LLM solo para campos de texto («copia tal cual»). Puertas: suma (`bases+IVA−IRPF+recargo=total`) e `IVA=Σ base×tipo`; si no cuadra → estado `revisar` con motivo; subtotal derivado marcado `derivado`. Respuesta: record + estado + evidencias por campo. Se guarda en la tabla SQL y se indexa en el mismo índice (doc_id = hash opaco del nº de factura, página = imagen). `GET /invoices/{id}/image`. Preguntas de factura vía `is_invoice_question` + plan JSON + `run_plan` integradas en `/ask` con citas (nº + campo + fragmento).

`POST /invoices` se ha retirado: la interfaz solo usa `/invoices/upload`. `GET /invoices` incluye estado y motivo. Las respuestas SQL advierten cuando incluyen facturas pendientes de revisión. Cada cita incluye `doc` visible y `doc_id` opaco para recuperar páginas; hay que regenerar el índice anterior. Los IDs distinguen PDF y factura. La fila, fragmentos y páginas se confirman en una transacción SQLite; el archivo de imagen se publica tras el commit.

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


## Revisión parcial del 31 de octubre de 2026

Las subidas tienen límites configurables `upload_pdf_max_bytes` (25 MiB), `upload_image_max_bytes` (10 MiB) y `upload_pdf_max_pages` (200). Devuelven 413 con `code` y `message`, leen por bloques y usan handlers síncronos. Se comprueba que los directorios de subida y sus entradas existentes se resuelvan dentro de `data_dir`; esta comprobación no evita carreras de sustitución de symlinks.

Los campos de texto sin evidencia OCR se anulan y se marcan `sin_evidencia`. Las comparaciones monetarias utilizan el mismo parser Decimal que la extracción, las sumas rechazan datos ausentes o inválidos, y la igualdad textual compara valores completos. El plan de consulta prioriza el número exacto y rechaza varias coincidencias normalizadas. Los adaptadores HTTP validan índices y dimensiones. Los embeddings de factura se calculan antes de escribir.

**Trabajo pendiente:** los casos de carreras de symlinks siguen sin resolverse. No se ha modificado el verificador de citas. La publicación del archivo ocurre después del commit SQLite: si falla el renombrado, la imagen sigue disponible desde la página guardada en SQLite.
Verificación parcial: 51 pruebas de servicio y 5 de scripts pasan; Ruff, formato y mypy pasan. Se reutilizó el entorno instalado del repositorio principal con `PYTHONPATH=src` y `UV_NO_SYNC=1`; no se instalaron dependencias. OpenAPI se regeneró desde este worktree.


## Ronda 2

`setup.download` verifica parciales completos y recupera errores 416; `install_llama` prepara una versión temporal y valida el marcador `VERSION`. Los tests usan archivos y servicios simulados; no descargan modelos ni ejecutan llama-server.

La UI actual todavía usa `doc` para abrir fuentes. El servidor admite ese nombre cuando es inequívoco, pero ante un PDF y una factura con el mismo nombre devuelve 404: la UI debe adoptar `doc_id` para desambiguar. Este ajuste queda fuera del ámbito de esta ronda.
