# Arquitectura

## Vista general
```
Navegador ──► Next.js (apps/web)  ── /api/* proxy fino (BFF) ──►  Servicio IA (services/ai, FastAPI)
               UI: tokens → shadcn/Base UI → componentes de dominio      │
               tipos TS generados de openapi.json                         ├─► llama-server :8081  LLM (Qwen3.5-4B, sin "pensar")
                                                                          ├─► llama-server :8082  embeddings (bge-m3)
                                                                          ├─► llama-server :8083  reranker (bge-reranker-v2-m3)
                                                                          ├─► llama-server :8084  OCR (GLM-OCR GGUF)
                                                                          └─► SQLite + sqlite-vec (fragmentos, páginas PNG, facturas)
```
Todo escucha en `127.0.0.1`. Nada sale de la máquina.

## Contrato
`services/ai/openapi.json` es la fuente de verdad. La web solo habla con el servicio a través de tipos generados (`openapi-typescript` + `openapi-fetch`). `mise run check` falla si hay drift.

## Capas del servicio

`api/` traduce HTTP y SSE. `application/` coordina casos de uso y define los puertos que consume. `domain/` contiene reglas y valores sin FastAPI, SQLite, HTTP ni configuración de entorno. `infra/` implementa los puertos con SQLite, archivos, PDF y clientes HTTP. `bootstrap.py` carga la configuración, conecta las implementaciones y expone la aplicación.

`tests/unit/test_architecture.py` analiza imports con `ast`. El test rechaza dependencias directas o transitivas que crucen los límites en sentido contrario, ciclos e imports dinámicos internos. También limita los módulos raíz a una lista cerrada. `api` nunca importa `infra`; solo `bootstrap.py` conecta todas las capas de la aplicación HTTP.

## Flujos
- **Documentos:** PDF → texto por sección (pdfplumber) → fragmentos con `chunk_id` determinista → embeddings → SQLite; cada página se renderiza a PNG (pypdfium2) para el visor. Reingesta idempotente.
- **Pregunta:** enrutador por reglas (¿factura o documentación?).
  - Documentación: vector ∪ BM25 → reranker → top-5 → LLM con salida JSON (responde o rechaza) → verificador de citas (la cita debe estar literalmente en el fragmento). Si no pasa → rechazo explícito.
  - Facturas (ADR-012): el LLM solo propone un plan JSON validado por esquema (intención valor/lista/contar/sumar, número, persona, campos, filtros, fechas). El código resuelve la persona (sin tildes ni mayúsculas, trigramas FTS5, erratas, NIF normalizado) y el número (exacto, normalizado, parcial, sin ceros), genera el SQL sobre una lista cerrada de columnas tipadas (`facturas_q`: fechas ISO, importes en céntimos) y da forma a la respuesta: un valor si se pide un valor, una lista solo si se pide una lista. Varias candidatas → aclaración estructurada (`clarification`, ADR-013) con las facturas candidatas y la pregunta que reenvía cada una; plan inválido → un reintento y después aclaración, sin caer al RAG. Solo se citan las facturas seleccionadas.
- **Factura (imagen):** OCR → reglas deterministas para importes (Decimal) → LLM solo para campos de texto → puertas de coherencia (suma e IVA). Si no cuadra → "revisar". Campos ausentes = `null`.

La comparación reproducible en `evidence/chunking/` muestra que las secciones mantienen íntegros seis hechos sintéticos que una ventana fija de 64 caracteres parte en cuatro casos. Es una prueba exploratoria de integridad literal, no de calidad de recuperación; no justifica generalizar a documentos sin encabezados o secciones largas.

## Bloques de respuesta (ADR-014)

`domain/invoices/blocks.py` construye fichas `key_data` y tablas `table` desde los datos seleccionados para la respuesta. El contrato añade `blocks_version: 1`, `blocks` y `follow_ups`. Los valores presentes llevan citas y las sumas referencian sus operandos. La web no calcula importes ni completa campos. `done` prevalece sobre el evento `blocks`; una versión desconocida o un bloque inválido hace que se muestre el Markdown completo. Véanse [ADR-014](decisions-log.md#adr-014-bloques-de-respuesta-derivados-de-evidencia-2026-11-01) y el [contrato](streaming.md).

## Concurrencia y admisión de consultas

`application/ask/capacity.py` limita por proceso a dos consultas activas y cuatro en espera. `api/routes.py` aplica el límite a `/ask` y `/ask/stream`, con espera máxima de 60 segundos. El flujo SSE informa de la espera mediante `step`; `queue_full` y `queue_timeout` terminan el flujo con un error recuperable. En `/ask` devuelven HTTP 503. La cola no es durable, no comparte capacidad entre procesos ni limita ingestas. No se han acreditado equidad ni carga sostenida.

La recuperación cierra SQLite antes de emitir el siguiente evento. `infra/pdf/lock.py` serializa el uso de PDFium entre ingestas y visor dentro del proceso. La carga sintética registrada en [CHANGELOG](CHANGELOG.md) no demuestra la causa del error histórico sin traza.

## Trazas disponibles

Los eventos SSE `step` y `done.timings` permiten reconstruir la última consulta en Sistema. El cliente conserva esa traza en memoria. El historial local persiste en SQLite WAL y la cola en memoria guarda el resultado fuera del stream. `HistoryRepository` define el contrato de escritura, consulta, borrado, retención y revisión; SQLite es la implementación actual. Las trazas internas opcionales son independientes. Las rutas locales requieren token y el proxy lo inyecta en servidor. La cola reintenta con backoff, incluso si SQLite falla al abrirse al inicio, pero pierde pendientes al reiniciar. Sistema distingue el fallo de apertura de la desactivación administrativa. La [propuesta de persistencia](design/persistencia-historial-feedback.md) conserva el diseño anterior; la implementación y sus límites se describen en [escalado](scaling-deployment.md).

## Modularidad (puertos y adaptadores)
LLM, embeddings, reranker y OCR son `Protocol`s de `application/ports`. `infra/models/http.py` contiene los clientes HTTP y `bootstrap.py` los crea desde `config/config.yaml`, validada con Pydantic al arrancar. Cambiar de modelo exige cambiar la configuración o el modelo que sirve llama-server.

## Por qué así (resumen; detalle en decisions-log.md)
- Python solo donde hace falta (modelos, OCR, índice); la web puede crecer sin tocar la IA.
- Reducir respuestas inventadas por diseño: el LLM nunca tiene la última palabra; el código verifica citas y aritmética y, si duda, rechaza. No hay aún una cifra de error validada (el gold no está aprobado).
- Límite conocido: el verificador es literal/heurístico; no prueba implicación semántica. La evaluación con LLM juez llega después.

## Fronteras y seguridad
- Todo en `127.0.0.1`; el proxy de Next reenvía solo `content-type`, `accept` y `accept-language`, recodifica cada segmento de ruta y comprueba el origen final (sin SSRF). Si el servicio cae, devuelve 502 `{code, message}`.
- Ficheros: `/ingest` solo admite rutas dentro de `data_dir` (sin `..`, absolutas ni symlinks que salgan); las subidas escriben en `data_dir/documents` y `data_dir/invoices` con nombre saneado, límite de tamaño y de páginas configurable, y 413 tipado.
- Documentos y facturas reales nunca entran en el repo ni en el ZIP: `.gitignore` + comprobación en `scripts/package.py`.

## Procesos y arranque
`mise run start` → `scripts/dev.py` (solo stdlib): comprueba puertos, lanza cada proceso en su propio grupo, espera su health check en orden (LLM, embeddings, reranker, OCR reutilizado si ya corre, IA, web) y, con Ctrl-C, para en dos fases (amable y luego forzado a los 5 s) con `atexit` de respaldo. `DOC_ASSISTANT_FAKE_LLAMA=1` sustituye los tres llama-server por un simulador para CI y pruebas.

## Calidad y evidencia
- `mise run check`: ruff, mypy (estricto en scripts), tests unitarios y de integración, tests de scripts, enlaces Markdown, deriva del contrato OpenAPI→TS, eslint, typecheck y build.
- `mise run check-links`: destinos locales de los Markdown; no valida anclas.
- `mise run test-live`: batería optativa contra `DOC_ASSISTANT_LIVE_LLM`.
- `mise run test-architecture`: límites del grafo de imports de las cuatro capas e inventario de entradas raíz.
- `mise run evidence`: capturas Playwright deterministas (API simulada con fixtures). `--live`: corrida real con documentos y facturas sintéticos → `evidence/live/results.md`.
- Revisión independiente por otro modelo: `docs/reviews/`, triaje en ADR-006.

## Entrega
`mise run package` crea un ZIP64 con código, docs, evidence, los cinco GGUF (con `models/SHA256SUMS`) y los binarios llama.cpp b12020 de macOS arm64, Linux x64 y Windows x64 en `vendor/archives/`. `setup` usa lo empaquetado antes de descargar nada (SHA256). El script descomprime en limpio y hace setup + start + pregunta para probarlo.

## Streaming y preguntas panorámicas
`POST /ask/stream` emite el mismo pipeline como eventos SSE (trazas, tokens provisionales, citas, rechazo o aclaración, `done`); la verificación corre tras el último token y puede retirar el texto. Las preguntas sobre capacidades, inventario o el índice de un documento se responden desde metadatos del índice, sin LLM. Detalle en [streaming](streaming.md) y ADR-009.

## Historial y feedback

Por defecto se guarda pregunta, respuesta, citas y `request_id` en `history.db`, junto al índice configurado. El administrador puede establecer `DOC_ASSISTANT_HISTORY_ENABLED=0` o ajustar `DOC_ASSISTANT_HISTORY_RETENTION_DAYS` (30 por defecto, mínimo 1). La purga se ejecuta al arrancar y cada hora. El borrado desde el panel invalida las escrituras y streams anteriores; también se puede usar `python -m doc_assistant.history_clear --url http://127.0.0.1:3000 --yes` con el proxy local en ejecución. El comando elimina historial y feedback.

El lanzador genera un token para API y proxy por ejecución. Si se arrancan por separado, ambos necesitan el mismo `DOC_ASSISTANT_HISTORY_TOKEN` secreto. No debe exponerse al navegador ni a otros equipos. La autorización es local, sin cuentas; no equivale a SSO. La organización debe validar las obligaciones legales y de protección de datos antes de desplegarlo.

```text
Respuesta incorrecta → pendiente → revisión humana → revisado → exportación JSONL
                                  ↳ comprobar fallo y ausencia de datos sensibles
```

El comentario es opcional. Sin consentimiento explícito, el feedback no copia la traza con pregunta, respuesta, documentos ni importes; el usuario puede elegir incluirla. La revisión añade una respuesta esperada y exige confirmar el fallo y la ausencia de datos sensibles. Solo se exportan elementos revisados con respuesta esperada, como candidatos para ampliar la evaluación, no como gold aprobado automáticamente. El chat confirma el envío de feedback; los fallos de guardado de historial se registran con `request_id` y aparecen en Sistema sin cambiar la respuesta.
