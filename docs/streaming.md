# API: consulta en streaming y catálogo de fuentes

Contrato de `POST /ask/stream` (SSE), `GET /sources`, `DELETE /sources/{id}` y `POST /sources/{id}/reindex`. El esquema exacto está en `services/ai/openapi.json` (`StreamEvent`, `Source`, `Suggestion`, `Clarification`, `KeyDataBlock`, `TableBlock`).

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

4b. `clarification` — la pregunta es ambigua y el servicio puede resolverla con candidatas reales. Sustituye a `refusal` en ese caso (nunca salen los dos):
   ```json
   {"reason":"invoice:aclaracion","clarification":{"prompt":"¿De qué factura?","detail":null,"total":2,"candidates":[{"doc":"FRA-1","doc_id":"inv-...","emisor":"...","cliente":"...","fecha":"07 marzo 2026","total":"1.706,60 €","question":"¿Cuál es el importe total de la factura FRA-1?"}]}}
   ```
   - `reason` ∈ `invoice:aclaracion`, `invoice:factura_ambigua`, `invoice:parte_ambigua`. El resto de `invoice:*` (`factura_no_encontrada`, `parte_no_encontrada`, `sin_resultados`...) siguen siendo `refusal`: no hay nada entre lo que elegir.
   - `prompt` es la pregunta corta que se muestra; `detail`, una frase de contexto cuando la hay (qué personas encajan, cuántas facturas hay).
   - `candidates` (como mucho 5) tiene `doc` (número de factura), `doc_id` y, solo si la factura los tiene, `emisor`, `cliente`, `fecha` y `total` tal cual están guardados. Ningún campo se rellena ni se deduce.
   - `question` es la pregunta original con la factura elegida nombrada, construida en el servicio con los campos que se pedían (`¿Cuál es el importe total de la factura X?`; si la pregunta no era de valor, `¿Qué datos tiene la factura X?`). El cliente la envía tal cual como pregunta nueva.
   - `total` cuenta todas las facturas que encajan; si es mayor que `candidates.length`, el cliente lo dice y sugiere acotar por número o fecha.
   - Sin tokens previos: no hay `retract`. `done` repite `clarification` y lleva `ok:false`, `reason` y `suggestions:[]`; `answer` conserva un texto plano («¿De qué factura? ¿Te refieres a alguna de estas? …») para clientes que no entienden el evento. `/ask` devuelve el mismo campo `clarification`.

4c. `blocks` contiene `{"blocks_version":1,"blocks":[...],"follow_ups":[...]}`. Es aditivo desde v0.14.0 y se emite tras `citations` cuando hay bloques o preguntas sugeridas. `done` repite estos campos y prevalece sobre el evento anticipado.
   - `key_data`: `title`, `doc_id`, `items[{field,label,text,kind,cite}]`, `note`. `text:null` indica ausencia. Cada valor presente referencia una cita del mismo documento y campo, cuyo `quote` coincide con el texto mostrado.
   - `table`: `title`, `columns[{key,label,kind}]`, `rows[{doc_id,question,cells}]`, `summary`, `note`. Cada celda sigue el orden de columnas; el número de factura también tiene cita. La pregunta de fila se genera en el servicio.
   - `summary`: `operation:"sum"`, `refs` de cada operando, `label`, `text` y `kind:"amount"`. El servicio calcula la suma con Decimal desde las filas seleccionadas; el cliente no calcula importes.
   - `kind` es `text | date | amount | percent | id`. `follow_ups` lleva `label` y `question`, derivadas de campos presentes o apartados recuperados. No implica memoria entre turnos.
   - El cliente solo presenta bloques al recibir el resultado final. Si la versión es desconocida, alguna estructura no es válida o una celda pierde su respaldo, muestra el Markdown completo. No conserva un subconjunto que pueda ocultar información.
   - Los clientes previos ignoran el evento y los campos nuevos. `answer` y `segments` conservan los valores, ausencias y advertencias para poder leer y copiar la respuesta sin bloques.

5. `done` — siempre el último evento si no hubo error. Es la verdad final (igual a la respuesta de `/ask` + tiempos):
   ```json
   {"ok":true,"answer":"...","citations":[...],"segments":[{"text":"...","refs":[0]}],"inline":"rules","reason":"verified","suggestions":[],"timings":{"route":0.0,"retrieve":0.08,"rerank":0.4,"generate":2.1,"verify":0.01,"total":2.6}}
   ```
   `segments` y `inline`: ver «Citas inline» más abajo.
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

### Citas inline (`segments`, `inline`)
`done` (y `/ask`) llevan `segments: {text, refs[]}[]`: la respuesta partida en trozos, donde `refs` son posiciones en `citations`.
Los `text` concatenados reconstruyen `answer` exactamente; un trozo sin `refs` no lleva marcador. `citations` viene ordenada por primer uso
(los marcadores se leen 1, 2, 3 a lo largo del texto) y contiene las citas usadas por los segmentos o por los bloques estructurados. Las citas adicionales de los bloques se añaden al final sin cambiar los índices anteriores; si ningún segmento tiene marcador, se
mantienen todas y se muestran tras la respuesta. `inline` dice quién colocó los marcadores:
- `template`: respuestas meta y de facturas, construidas por plantilla con una cita por elemento listado.
- `rules` (por defecto): asignación determinista por frase. Una cita respalda una frase si cubre sus cifras y, al menos, la mitad de sus raíces de palabra.
- `model`: el LLM emite los segmentos con ids de fragmento; cada segmento se valida (ids existentes, texto que reconstruye la respuesta, respaldo por frase). Si no valida, se degrada a `rules`.
- `none`: sin segmentos; el cliente muestra las citas al final.
Se elige con `inline_citations: rules | model | off` en la configuración. Los números de gold-v2 que justifican el valor por defecto están en ADR-011.
Los marcadores no cambian el veredicto del verificador: se calculan después de verificar.

### Resaltado en la página: `GET /sources/{id}/pages/{n}/highlight?quote=...`
Devuelve `PageHighlight {page, found, reason, rects[]}` con rectángulos como fracciones de la página (origen arriba a la izquierda),
calculados al vuelo con el texto del PDF (pypdfium2) y la cita literal. `reason` ∈ `ok`, `not_found` (no aparece en la capa de texto),
`no_positions` (facturas: la imagen pasa por OCR y no se guardan posiciones), `no_file` (el PDF original ya no está). No hay migración
de esquema: las posiciones no se guardan en el índice.

### Progreso de subida: `?job=<id>` y `GET /ingest/jobs/{job_id}/events` (SSE)
`POST /documents` y `POST /invoices/upload` aceptan `?job=<id>` (8–64 caracteres `A-Za-z0-9_-`, lo elige el cliente). Mientras procesan, publican
etapas que se siguen con `GET /ingest/jobs/{id}/events` (`event: stage`, `IngestStageEvent {stage, label, seq, detail}`):
`received`, `reading` (PDF), `ocr` y `extracting` (factura), `indexing`, y `done` o `error` al final. Los trabajos viven en memoria
15 minutos: un reinicio los pierde y la respuesta de la subida sigue siendo la verdad. Un trabajo que no aparece en 30 s cierra el stream.

### Tipos nuevos
```ts
type Suggestion = { doc: string; doc_id: string; section: string; heading: string | null; pages: number[] };
// AskResponse gana: suggestions: Suggestion[] (default [])
type Clarification = { prompt: string; detail: string | null; total: number; candidates: ClarificationCandidate[] };
type ClarificationCandidate = { doc: string; doc_id: string; emisor: string | null; cliente: string | null; fecha: string | null; total: string | null; question: string };
// AskResponse (y DoneEvent) gana: clarification: Clarification | null
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

## Evidencia de facturas

Las citas SQL corresponden al dato extraído y almacenado en InvoiceDB. `chunk_id` identifica número y campo, `quote` y `fragment` muestran el mismo formato determinista que la celda. No acreditan una posición literal del OCR. El visor de imagen de factura informa de la ausencia de posiciones y permite contrastar el original.

El contrato público se exporta desde Pydantic a `services/ai/openapi.json` y de ahí a `schema.d.ts`. `blocks_version: 1` versiona la representación nueva sin cambiar la versión histórica global del API. `mise run check` comprueba su deriva.

Los errores del modelo terminan el flujo con `error`, sin `done`. El código `model_busy` indica una respuesta HTTP 429 o 503 del modelo; `model_timeout` indica que se agotó la espera. El mensaje propone reintentar y no incluye la dirección del modelo. Estos códigos también pueden aparecer en errores de ingesta.

Cada proceso del servicio admite dos consultas activas y cuatro en espera. Una consulta SSE en espera recibe un paso `route` con el texto «Esperando turno para responder». Si la cola está llena, el servicio termina el flujo con `queue_full`; si la espera supera 60 segundos, usa `queue_timeout`. En `/ask` ambos casos devuelven HTTP 503 con el mismo código. La cola es en memoria, no es durable ni compartida entre procesos y no limita las ingestas. El tiempo de cola no se suma al `timings.total` de la respuesta.

## Identificador de petición

Las respuestas de `/ask` y `/ask/stream` incluyen `x-request-id` para las peticiones aceptadas por el endpoint. El evento `done` repite el mismo UUID. Los errores del flujo conservan el identificador en la cabecera. El identificador aún no implica que exista una traza persistida.
