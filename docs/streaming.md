# API: consulta en streaming y catálogo de fuentes

Contrato de `POST /ask/stream` (SSE), `GET /sources`, `DELETE /sources/{id}` y `POST /sources/{id}/reindex`. El esquema exacto está en `services/ai/openapi.json` (`StreamEvent`, `Source`, `Suggestion`).

Desde la web se accede por el proxy igual que hoy: `/api/ask/stream`, `/api/sources`, ...

## 1. `POST /ask/stream` (SSE)

Body: igual que `/ask` → `{"question": "..."}` (1..1000 caracteres).
Respuesta: `200 text/event-stream`. Cada evento:

```
event: <tipo>
data: <JSON en una línea>

```
Errores de validación del body → `422` JSON normal (no stream). Cualquier fallo después de abrir el stream → evento `error` y fin.
El stream SIEMPRE termina con exactamente un `done` o un `error`. `/ask` (no streaming) se mantiene igual.

Nota: en el JSON de `data:` NO va el campo `event` (es el nombre del evento SSE). Los tipos TS lo incluyen como discriminante:
al parsear, haz `{event: <nombre SSE>, ...JSON.parse(data)}`. Usa `fetch` + `ReadableStream` (no `EventSource`, que solo hace GET).
El proxy actual de Next ya devuelve `upstream.body` como stream; comprobar que no bufferiza (cabeceras `Cache-Control: no-cache`, `X-Accel-Buffering: no`).

### Tipos de evento (orden típico)

1. `step` — traza del pipeline. Se emite al empezar (`status:"running"`) y al acabar (`status:"done"`) cada paso.
   ```json
   {"id":"retrieve","status":"running","label":"Buscando fragmentos","data":{}}
   {"id":"retrieve","status":"done","label":"12 fragmentos candidatos","data":{"n":12},"elapsed_s":0.08}
   ```
   `id` ∈ `route` (clasificar la pregunta), `invoices` (consulta de facturas), `meta` (respuesta desde el índice),
   `retrieve`, `rerank`, `generate`, `verify`. `label` es texto humano en español, listo para mostrar.
   `data` opcional: `n` (nº fragmentos), `top` (lista de `{doc, section}` tras reordenar), `intent`, `n_citations`.
   No todos los pasos aparecen siempre (p.ej. una pregunta meta no tiene `retrieve`/`generate`).

2. `token` — texto incremental de la respuesta: `{"text":"El alcance "}`. Concatenar en orden.
   **Los tokens son PROVISIONALES** hasta `verify`: la UI debe mostrarlos con un estado "verificando fuentes…"
   (p.ej. opacidad/cursor/badge) y no permitir copiar como respuesta final hasta `done`.

3. `citations` — `{"citations": Citation[]}` (mismo `Citation` que `/ask`). Solo si la verificación final pasó.

4. `refusal` — `{"answer":"No dispongo de esa información en los documentos","reason":"verify:...","retract":true,"suggestions":[Suggestion...]}`
   - `retract: true` ⇒ hubo tokens provisionales y NO pasaron la verificación: **la UI debe borrar el texto
     acumulado y sustituirlo por `answer`** (rechazo). `retract: false` ⇒ no se había emitido texto.
   - `suggestions`: fuentes relacionadas reales (lo más cercano que se encontró), para mostrar "Quizá te sirva:".

5. `done` — siempre el último evento si no hubo error. Es la verdad final (igual a la respuesta de `/ask` + tiempos):
   ```json
   {"ok":true,"answer":"...","citations":[...],"reason":"verified","suggestions":[],"timings":{"route":0.0,"retrieve":0.08,"rerank":0.4,"generate":2.1,"verify":0.01,"total":2.6}}
   ```
   Recomendación: al recibir `done`, renderizar SIEMPRE desde `done.answer` / `done.citations` (descartando los tokens).

6. `error` — `{"code":"adapter_error","message":"No responde el servidor en ..."}`. Si había tokens, se descartan.

### Garantía de fundamentación en streaming (compromiso)
- El LLM genera JSON con esquema (`answerable`, `answer`, `citations`, en el orden de `answer_mode`). Del JSON
  parcial se extrae solo el valor de `answer` y se emite como `token`s. Con `answer_mode: decide_first` (el actual)
  las citas llegan DESPUÉS del texto; con `evidence_first` llegan antes y se comprueban como literales antes del primer token.
- La verificación completa (cifras y unidades de la respuesta respaldadas por las citas, negaciones, inyección)
  solo puede hacerse con la respuesta entera ⇒ se ejecuta tras el último token. Si falla: `refusal` con `retract:true`.
- Por eso los tokens son provisionales y la UI debe marcarlos así. Nunca se emite `citations` para una respuesta no verificada.

### Respuestas meta / panorámicas (nuevo)
Preguntas tipo "¿qué sabes hacer?", "¿qué documentos tienes?", "resúmeme lo que hay", "¿de qué trata <doc>?"
se responden desde los metadatos reales del índice (sin LLM). Salen como `ok:true`, `reason:"meta:<tipo>"`
(`meta:capabilities`, `meta:inventory`, `meta:document`), con `token`s (el texto completo en trozos) y `citations`
apuntando a los fragmentos cuyos títulos de sección se listan (quote = título literal). En `/ask` igual (mismos campos).

### Tipos nuevos
```ts
type Suggestion = { doc: string; doc_id: string; section: string; heading: string | null; pages: number[] };
// AskResponse gana: suggestions: Suggestion[] (default [])
```

## 2. Fuentes

### `GET /sources` → `Source[]`
```ts
type Source = {
  id: string;            // doc_id opaco: "pdf-..." o "inv-..." (usar tal cual en URLs)
  kind: "pdf" | "invoice";
  name: string;          // nombre visible (fichero sin extensión, o nº de factura)
  title: string | null;  // título detectado del PDF
  n_pages: number;       // páginas renderizadas (facturas: 1 si hay imagen, si no 0)
  n_chunks: number;
  sections: { section: string; heading: string | null; pages: number[] }[];
  added_at: string | null;   // ISO 8601 (mtime del fichero guardado), null si no se conoce
  status: "indexed" | "review" | "no_text";   // review = factura que no cuadra; no_text = PDF sin capa de texto
  status_detail: string | null;               // motivo (p.ej. de la factura)
  file: string | null;       // ruta relativa a data_dir
};
```
Orden: PDFs por nombre, después facturas por número.

### `DELETE /sources/{id}` → `204`
Quita la fuente del índice (fragmentos, vectores, páginas; si es factura, también su fila). El fichero NO se borra:
se mueve a `data_dir/_removed/`. `404` ErrorBody si no existe.

### `POST /sources/{id}/reindex` → `IngestResponse` (como `/ingest`)
Solo PDFs con fichero en `data_dir/documents/`. Facturas → `400 {code:"not_reindexable"}` (requieren OCR; volver a subir). `404` si no existe.

## Petición al servicio AI: endpoint de salud por pieza

Propuesta: `GET /health/components` devuelve `{ "components": [{ "id": "web" | "proxy" | "ai" | "llm" | "embeddings" | "reranker" | "ocr" | "sqlite", "status": "ok" | "degraded" | "unavailable" | "unknown", "latency_ms": number | null, "detail": string | null }] }`. Una latencia nula indica que no se ha medido. El cliente presenta `unknown` cuando no existe el endpoint y no inventa disponibilidad ni latencias.
