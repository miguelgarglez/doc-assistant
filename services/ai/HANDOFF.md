# Servicio de IA: handoff

Paquete `doc_assistant` en `src/`, Python 3.12 o superior, gestionado con uv. Se migraron adaptadores, fragmentación, ingesta, facturas, almacenamiento, preguntas y verificador del slice; no se migraron evaluación ni datos reales. El verificador conserva las reglas del original. Los puertos LLM, embeddings, reranker y OCR son Protocols; OCR es una interfaz reservada, sin implementación conectada a la ingesta.

La configuración se valida con Pydantic al arrancar y está en `../../config/config.yaml`. Las rutas relativas se resuelven desde ese archivo. Ajusta los endpoints de modelos antes de usar `/ingest` y `/ask`; los valores incluidos son ejemplos locales. Cada PDF se identifica por el nombre sin extensión: nombres iguales en distintas carpetas representan el mismo documento. La reingesta sustituye sus fragmentos y páginas PNG en SQLite; los ID de fragmentos son deterministas. Un PDF sin texto produce una advertencia y sus páginas siguen disponibles. La API ofrece `/health`, `/ingest`, `/ask`, `/sources/{doc_id}/pages/{n}` y `/invoices`; la respuesta de preguntas incluye citas verificadas o un rechazo. La verificación es heurística y no demuestra que la respuesta esté implicada semánticamente por la fuente.

Desde `services/ai`:

```sh
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python -m doc_assistant.export_openapi
uv run uvicorn doc_assistant.api:app
```

Última comprobación: 29 tests pasan, Ruff y mypy strict sin errores; OpenAPI generado en `openapi.json`. Starlette emite un aviso de deprecación del transporte httpx de TestClient. Las pruebas emplean PDFs y facturas sintéticos y adaptadores falsos; no prueban servidores de modelos reales.
