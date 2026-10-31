# Arquitectura

## Vista general
```
Navegador ──► Next.js (apps/web)  ── /api/* proxy fino (BFF) ──►  Servicio IA (services/ai, FastAPI)
               UI: tokens → shadcn/Base UI → componentes de dominio      │
               tipos TS generados de openapi.json                         ├─► llama-server :8081  LLM (Qwen3.5-4B, sin "pensar")
                                                                          ├─► llama-server :8082  embeddings (bge-m3)
                                                                          ├─► llama-server :8083  reranker (bge-reranker-v2-m3)
                                                                          ├─► Ollama :11434       OCR (GLM-OCR)
                                                                          └─► SQLite + sqlite-vec (fragmentos, páginas PNG, facturas)
```
Todo escucha en `127.0.0.1`. Nada sale de la máquina.

## Contrato
`services/ai/openapi.json` es la fuente de verdad. La web solo habla con el servicio a través de tipos generados (`openapi-typescript` + `openapi-fetch`). `mise run check` falla si hay drift.

## Flujos
- **Documentos:** PDF → texto por sección (pdfplumber) → fragmentos con `chunk_id` determinista → embeddings → SQLite; cada página se renderiza a PNG (pypdfium2) para el visor. Reingesta idempotente.
- **Pregunta:** enrutador por reglas (¿factura o documentación?).
  - Documentación: vector ∪ BM25 → reranker → top-5 → LLM con salida JSON (responde o rechaza) → verificador de citas (la cita debe estar literalmente en el fragmento). Si no pasa → rechazo explícito.
  - Facturas: el LLM solo traduce la pregunta a un plan JSON; el código lo ejecuta sobre la tabla SQL y cita nº de factura + campo. Campo nulo o factura inexistente → rechazo.
- **Factura (imagen):** OCR → reglas deterministas para importes (Decimal) → LLM solo para campos de texto → puertas de coherencia (suma e IVA). Si no cuadra → "revisar". Campos ausentes = `null`.

## Modularidad (puertos y adaptadores)
LLM, embeddings, reranker y OCR son `Protocol`s; los adaptadores HTTP se eligen en `config/config.yaml` (validada con Pydantic al arrancar). Cambiar de modelo = cambiar config o el modelo que sirve llama-server.

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
- `mise run check`: ruff, mypy (estricto en scripts), pytest (servicio y scripts), deriva del contrato OpenAPI→TS, eslint, typecheck y build.
- `mise run evidence`: capturas Playwright deterministas (API simulada con fixtures). `--live`: corrida real con documentos y facturas sintéticos → `evidence/live/results.md`.
- Revisión independiente por otro modelo: `docs/reviews/`, triaje en ADR-006.

## Entrega
`mise run package` crea un ZIP64 con código, docs, evidence, los tres GGUF (con `models/SHA256SUMS`) y los binarios llama.cpp b12020 de macOS arm64, Linux x64 y Windows x64 en `vendor/archives/`. `setup` usa lo empaquetado antes de descargar nada (SHA256). El script descomprime en limpio y hace setup + start + pregunta para probarlo.
