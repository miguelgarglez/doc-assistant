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
- Cero alucinación como propiedad de diseño: el LLM nunca es la última palabra; el código verifica citas y aritmética.
- Límite conocido: el verificador es literal/heurístico; no prueba implicación semántica. La evaluación con LLM juez llega después.
