# Evolución por versión

Galerías históricas generadas por `mise run evolution` (scripts/evolution.py) desde los tags anotados de git. La nota de integración de v0.13.0 se mantiene al final.
Las capturas son las que estaban versionadas en ese tag (`git show <tag>:evidence/screenshots/…`);
el texto es el mensaje del tag.

Nota de honestidad: al publicar se reescribió el historial (nombre público y fixtures neutros).
Las capturas versionadas de cada commit se regeneraron entonces ejecutando el e2e del código
de ese mismo commit, porque las originales mostraban la marca y fixtures anteriores.

## v0.1.0 · 2026-10-31 12:32 +0100 · commit `e9ca554`

**v0.1.0 — Build reproducible: mise + scripts Python, arranque único y contrato**

Qué cambió:
- Monorepo: services/ai (FastAPI migrado del slice, puertos/adaptadores, config validada) y apps/web (Next 16 + shadcn sobre Base UI, componentes de dominio con datos de ejemplo).
- mise.toml fija node/pnpm/python/uv; scripts/setup.py, dev.py y check.py (stdlib, multiplataforma); llama.cpp b12020 con SHA256; fake_llama para CI.
- openapi.json como contrato; tipos TS generados; check falla si hay deriva.
- README de evaluador, ADR-001..005, workflow cross-platform (no ejecutado).

Qué se probó (CHECKPOINT 12:24–12:32):
- mise run check → OK (ruff, mypy, 29 tests, contrato sin deriva, eslint, tsc, next build).
- mise run start + Ctrl-C → todo cerrado en ~1 s, puertos libres, sin huérfanos (modelos reales y fake). Puerto ocupado → código 2.
- Windows: no probado.

_Sin capturas en esta versión._

## v0.2.0 · 2026-10-31 12:40 +0100 · commit `5f182b4`

**v0.2.0 — Primera pregunta real extremo a extremo**

Qué cambió:
- llama-server del LLM con --reasoning-budget 0 (Qwen "pensaba" y cada /ask caducaba a los 90 s).
- CHECKPOINT con horas reales, "Qué se probó" y "Decisión clave".

Qué se probó (CHECKPOINT 12:40, prueba de humo, no evaluación):
- Ingesta por el proxy de Next de 4 PDFs de prueba no versionados → 44 fragmentos en 1,8 s.
- Pregunta de especificación sobre un datasheet → valor correcto con cita de sección y página, 7 s.
- Pregunta de precio → rechazo, 5 s. GET página → 200 image/png.
- Sin UI conectada aún: sin capturas.

_Sin capturas en esta versión._

## v0.3.0 · 2026-10-31 12:50 +0100 · commit `7068e08`

**v0.3.0 — Web conectada al API real y setup sin redescargas**

Qué cambió:
- Cliente tipado openapi-fetch; la página pregunta a /ask, muestra citas y abre la página con el fragmento resaltado; rechazo y error visibles.
- Playwright con API simulada → capturas deterministas en evidence/screenshots.
- Setup: carpeta de modelos --models-dir > DOC_ASSISTANT_MODELS_DIR > .env.local > ./models; solo descarga lo que falta, con reanudación y confirmación > 1 GB.
- Ollama (GLM-OCR) en el arranque, reutilizado si ya corre.

Qué se probó (CHECKPOINT 12:47–12:48):
- mise run check → OK; pnpm e2e → 3 passed, capturas idénticas al regenerar.
- setup --models-dir <carpeta de modelos> --verify → 3 modelos SHA256 OK, nada descargado; start usa .env.local.
- Conocido: textos de dominio erróneos ("revisión fiscal") y tipografía monoespaciada en las capturas.

![v0.3.0 ask-answer-with-source](v0.3.0/ask-answer-with-source.png)
![v0.3.0 ask-error](v0.3.0/ask-error.png)
![v0.3.0 ask-refusal](v0.3.0/ask-refusal.png)

## v0.4.0 · 2026-10-31 13:12 +0100 · commit `3ec2f47`

**v0.4.0 — Fase 2: auditoría de tests, documentos, facturas y pulido web**

Qué cambió:
- Auditoría de los 81 tests del slice: 26 migrados, 55 excluidos a propósito (evaluación), 0 perdidos.
- /ingest confinado a data_dir; POST /documents (subida idempotente por hash).
- Facturas: OCR GLM → reglas Decimal para importes → LLM para texto; puertas de suma e IVA → "revisar"; SQL en /ask con citas.
- Web: dominio corregido (título de producto), visor lado a lado, navegación de citas, estados, capturas escritorio y móvil.
- Arreglos del integrador: fuente Geist autorreferente y Courier forzado en e2e; el proxy reenviaba Expect (rompía subidas).

Qué se probó (CHECKPOINT 13:16):
- mise run check → exit 0 (42 + 5 tests); pnpm e2e → 6 passed, capturas estables.
- Stack real con datos sintéticos: 6/6 facturas estado ok, 0 discrepancias en número, base, IVA, IRPF y total; "importe total de F-2026-001" → 537.94 con cita SQL; "precio del robot" → rechazo.
- Limitaciones: agregados ("suma del IVA de todas") se rechazan; fecha sin normalizar.

![v0.4.0 ask-answer-with-source-mobile](v0.4.0/ask-answer-with-source-mobile.png)
![v0.4.0 ask-answer-with-source](v0.4.0/ask-answer-with-source.png)
![v0.4.0 ask-error-mobile](v0.4.0/ask-error-mobile.png)
![v0.4.0 ask-error](v0.4.0/ask-error.png)
![v0.4.0 ask-refusal-mobile](v0.4.0/ask-refusal-mobile.png)
![v0.4.0 ask-refusal](v0.4.0/ask-refusal.png)

## v0.5.0 · 2026-10-31 13:33 +0100 · commit `d0ce091`

**v0.5.0 — Revisión aplicada, facturas en la web, empaquetado y evidencia regenerable**

Qué cambió:
- ADR-006: triage de la revisión gpt-6.1-sol (25 hallazgos); aplicados límites de subida (413), confinamiento de symlinks, campos sin evidencia a null, doc_id opaco por tipo, transacción de facturas, estado/motivo en GET /invoices, validación de adaptadores; proxy con allowlist de cabeceras, rutas validadas, 502/503 tipados.
- Web: pestañas Consulta/Facturas, subida, InvoiceReviewCard, fuentes Geist arregladas.
- Setup robusto (.part con SHA, extracción atómica, archivos locales en vendor/archives); dev.py ignora señales durante la parada.
- mise run package (ZIP64 + NOTICE), mise run evidence [--live], mise run evolution; esquema SQLite versionado.

Qué se probó (CHECKPOINT 13:33):
- mise run check → OK (55 + 7 tests); pnpm e2e → 11 passed.
- evidence --live: 6/6 facturas sintéticas ok sin discrepancias; preguntas con cita; 2 rechazos.
- package --no-models --smoke fake → OK (antes de la ronda 2 de revisión). Pendiente: paquete con modelos y smoke real; Windows no probado.

![v0.5.0 ask-answer-with-source-mobile](v0.5.0/ask-answer-with-source-mobile.png)
![v0.5.0 ask-answer-with-source](v0.5.0/ask-answer-with-source.png)
![v0.5.0 ask-error-mobile](v0.5.0/ask-error-mobile.png)
![v0.5.0 ask-error](v0.5.0/ask-error.png)
![v0.5.0 ask-refusal-mobile](v0.5.0/ask-refusal-mobile.png)
![v0.5.0 ask-refusal](v0.5.0/ask-refusal.png)
![v0.5.0 invoice-ok-mobile](v0.5.0/invoice-ok-mobile.png)
![v0.5.0 invoice-ok](v0.5.0/invoice-ok.png)
![v0.5.0 invoice-review-mobile](v0.5.0/invoice-review-mobile.png)
![v0.5.0 invoice-review](v0.5.0/invoice-review.png)

## v0.6.0 · 2026-10-31 13:41 +0100 · commit `30ed6f5`

**v0.6.0 — Nombre público doc-assistant, cobertura de requisitos, huecos y escalado**

Qué cambió:
- Renombrado a doc-assistant (paquete doc_assistant, DOC_ASSISTANT_*, UI "Doc Assistant", fixture e2e neutra, pie genérico en el troceado).
- docs/requirements-coverage.md, docs/open-gaps.md; scaling-deployment.md ampliado a toda la empresa.
- .DS_Store fuera de git; docs/repo-structure actualizado.

Qué se probó (CHECKPOINT 13:42):
- mise run check → OK; mise run evidence → 11 passed.
- Auditoría: 0 ficheros del material del reto en el historial; el historial aún contiene el nombre antiguo y referencias a un documento del material del reto (no publicado).

![v0.6.0 ask-answer-with-source-mobile](v0.6.0/ask-answer-with-source-mobile.png)
![v0.6.0 ask-answer-with-source](v0.6.0/ask-answer-with-source.png)
![v0.6.0 ask-error-mobile](v0.6.0/ask-error-mobile.png)
![v0.6.0 ask-error](v0.6.0/ask-error.png)
![v0.6.0 ask-refusal-mobile](v0.6.0/ask-refusal-mobile.png)
![v0.6.0 ask-refusal](v0.6.0/ask-refusal.png)
![v0.6.0 invoice-ok-mobile](v0.6.0/invoice-ok-mobile.png)
![v0.6.0 invoice-ok](v0.6.0/invoice-ok.png)
![v0.6.0 invoice-review-mobile](v0.6.0/invoice-review-mobile.png)
![v0.6.0 invoice-review](v0.6.0/invoice-review.png)

## v0.6.1 · 2026-10-31 14:02 +0100 · commit `0652ef0`

**v0.6.1 — Historial reescrito y auditado para publicar**

Nombre público y fixtures neutros en todo el historial; capturas regeneradas por commit; tags recreados.
Probado: mise run check OK, e2e 11 passed, auditoría de publicación 0 hallazgos.

![v0.6.1 ask-answer-with-source-mobile](v0.6.1/ask-answer-with-source-mobile.png)
![v0.6.1 ask-answer-with-source](v0.6.1/ask-answer-with-source.png)
![v0.6.1 ask-error-mobile](v0.6.1/ask-error-mobile.png)
![v0.6.1 ask-error](v0.6.1/ask-error.png)
![v0.6.1 ask-refusal-mobile](v0.6.1/ask-refusal-mobile.png)
![v0.6.1 ask-refusal](v0.6.1/ask-refusal.png)
![v0.6.1 invoice-ok-mobile](v0.6.1/invoice-ok-mobile.png)
![v0.6.1 invoice-ok](v0.6.1/invoice-ok.png)
![v0.6.1 invoice-review-mobile](v0.6.1/invoice-review-mobile.png)
![v0.6.1 invoice-review](v0.6.1/invoice-review.png)

## v0.7.0 · 2026-10-31 14:14 +0100 · commit `3f99b6d`

**v0.7.0 — Paquete completo probado y revisión #13/#14/#19/#23**

Qué cambió: visor por páginas del fragmento (#23); CI en push/PR (#19); cierre de procesos huérfanos (#14); aviso de OCR no listo (#13, parcial); licencias en licenses/; smoke real con factura y puertos.
Qué se probó: mise run check OK; e2e 12 passed; package --smoke real OK (4,09 GB, setup sin descargas, pregunta con cita, factura extraída, puertos liberados).

![v0.7.0 ask-answer-with-source-mobile](v0.7.0/ask-answer-with-source-mobile.png)
![v0.7.0 ask-answer-with-source](v0.7.0/ask-answer-with-source.png)
![v0.7.0 ask-error-mobile](v0.7.0/ask-error-mobile.png)
![v0.7.0 ask-error](v0.7.0/ask-error.png)
![v0.7.0 ask-refusal-mobile](v0.7.0/ask-refusal-mobile.png)
![v0.7.0 ask-refusal](v0.7.0/ask-refusal.png)
![v0.7.0 invoice-ok-mobile](v0.7.0/invoice-ok-mobile.png)
![v0.7.0 invoice-ok](v0.7.0/invoice-ok.png)
![v0.7.0 invoice-review-mobile](v0.7.0/invoice-review-mobile.png)
![v0.7.0 invoice-review](v0.7.0/invoice-review.png)

## v0.8.0 · 2026-10-31 15:00 +0100 · commit `cce6f39`

**v0.8.0 · OCR de facturas dentro del ZIP**

Qué cambió:
- GLM-OCR GGUF en llama-server :8084 por defecto; Ollama como alternativa (DOC_ASSISTANT_OCR_RUNTIME=ollama).
- assets.json con los dos GGUF (commit y SHA256); NOTICE con licencia MIT del modelo base y la duda.
- Parser de importes: tipos entre paréntesis, base sin tipo y TOTAL FACTURA.

Qué se probó:
- mise run check OK; e2e 12 passed; mise run package --smoke real OK (ZIP 5,53 GB, OCR desde models/ del ZIP).

![v0.8.0 ask-answer-with-source-mobile](v0.8.0/ask-answer-with-source-mobile.png)
![v0.8.0 ask-answer-with-source](v0.8.0/ask-answer-with-source.png)
![v0.8.0 ask-error-mobile](v0.8.0/ask-error-mobile.png)
![v0.8.0 ask-error](v0.8.0/ask-error.png)
![v0.8.0 ask-refusal-mobile](v0.8.0/ask-refusal-mobile.png)
![v0.8.0 ask-refusal](v0.8.0/ask-refusal.png)
![v0.8.0 invoice-ok-mobile](v0.8.0/invoice-ok-mobile.png)
![v0.8.0 invoice-ok](v0.8.0/invoice-ok.png)
![v0.8.0 invoice-review-mobile](v0.8.0/invoice-review-mobile.png)
![v0.8.0 invoice-review](v0.8.0/invoice-review.png)

## v0.9.0 · 2026-10-31 15:35 +0100 · commit `af84b3d`

**v0.9.0 · UI/UX del chat y sistema de diseño con temas**

Qué cambió:
- Temas intercambiables industrial (por defecto) y neutral, modo claro/oscuro, página /design, docs/design-system.md (ADR-007).
- Chat: atajos (Enter, Shift+Enter, Cmd/Ctrl+Enter, Cmd/Ctrl+K, Esc, flechas, ?), copiar respuesta/cita/Markdown con citas, pegar/arrastrar PDF e imagen con progreso, cancelar, regenerar, rechazo con diseño propio, auto-scroll que respeta al usuario.
- Revisión independiente con 13 hallazgos corregidos.

Qué se probó:
- mise run check OK; e2e 38 passed; axe 0 violaciones serias/críticas en home y /design, ambos temas y modos; CLS < 0.1.

![v0.9.0 ask-answer-with-source-mobile](v0.9.0/ask-answer-with-source-mobile.png)
![v0.9.0 ask-answer-with-source](v0.9.0/ask-answer-with-source.png)
![v0.9.0 ask-error-mobile](v0.9.0/ask-error-mobile.png)
![v0.9.0 ask-error](v0.9.0/ask-error.png)
![v0.9.0 ask-refusal-mobile](v0.9.0/ask-refusal-mobile.png)
![v0.9.0 ask-refusal](v0.9.0/ask-refusal.png)
![v0.9.0 design-industrial-mobile](v0.9.0/design-industrial-mobile.png)
![v0.9.0 design-industrial](v0.9.0/design-industrial.png)
![v0.9.0 design-neutral-mobile](v0.9.0/design-neutral-mobile.png)
![v0.9.0 design-neutral](v0.9.0/design-neutral.png)
![v0.9.0 invoice-ok-mobile](v0.9.0/invoice-ok-mobile.png)
![v0.9.0 invoice-ok](v0.9.0/invoice-ok.png)
![v0.9.0 invoice-review-mobile](v0.9.0/invoice-review-mobile.png)
![v0.9.0 invoice-review](v0.9.0/invoice-review.png)
![v0.9.0 theme-industrial-mobile](v0.9.0/theme-industrial-mobile.png)
![v0.9.0 theme-industrial](v0.9.0/theme-industrial.png)
![v0.9.0 theme-neutral-mobile](v0.9.0/theme-neutral-mobile.png)
![v0.9.0 theme-neutral](v0.9.0/theme-neutral.png)

## v0.10.0 · 2026-10-31 16:27 +0100 · commit `96a63bb`

**v0.10.0: chat con streaming, fuentes y sistema**

SSE verificado por proxy; integración de panorámicas y ADR-009. Playwright: 69 pruebas en tres pasadas. axe sin violaciones serias o críticas en cuatro rutas, dos temas y dos modos. mise run check correcto; salud por pieza pendiente del servicio.

![v0.10.0 ajustes-industrial-mobile](v0.10.0/ajustes-industrial-mobile.png)
![v0.10.0 ajustes-industrial](v0.10.0/ajustes-industrial.png)
![v0.10.0 ajustes-neutral-mobile](v0.10.0/ajustes-neutral-mobile.png)
![v0.10.0 ajustes-neutral](v0.10.0/ajustes-neutral.png)
![v0.10.0 ask-answer-with-source-mobile](v0.10.0/ask-answer-with-source-mobile.png)
![v0.10.0 ask-answer-with-source](v0.10.0/ask-answer-with-source.png)
![v0.10.0 ask-error-mobile](v0.10.0/ask-error-mobile.png)
![v0.10.0 ask-error](v0.10.0/ask-error.png)
![v0.10.0 ask-refusal-mobile](v0.10.0/ask-refusal-mobile.png)
![v0.10.0 ask-refusal](v0.10.0/ask-refusal.png)
![v0.10.0 design-industrial-mobile](v0.10.0/design-industrial-mobile.png)
![v0.10.0 design-industrial](v0.10.0/design-industrial.png)
![v0.10.0 design-neutral-mobile](v0.10.0/design-neutral-mobile.png)
![v0.10.0 design-neutral](v0.10.0/design-neutral.png)
![v0.10.0 fuentes-industrial-mobile](v0.10.0/fuentes-industrial-mobile.png)
![v0.10.0 fuentes-industrial](v0.10.0/fuentes-industrial.png)
![v0.10.0 fuentes-neutral-mobile](v0.10.0/fuentes-neutral-mobile.png)
![v0.10.0 fuentes-neutral](v0.10.0/fuentes-neutral.png)
![v0.10.0 invoice-ok-mobile](v0.10.0/invoice-ok-mobile.png)
![v0.10.0 invoice-ok](v0.10.0/invoice-ok.png)
![v0.10.0 invoice-review-mobile](v0.10.0/invoice-review-mobile.png)
![v0.10.0 invoice-review](v0.10.0/invoice-review.png)
![v0.10.0 sistema-industrial-mobile](v0.10.0/sistema-industrial-mobile.png)
![v0.10.0 sistema-industrial](v0.10.0/sistema-industrial.png)
![v0.10.0 sistema-neutral-mobile](v0.10.0/sistema-neutral-mobile.png)
![v0.10.0 sistema-neutral](v0.10.0/sistema-neutral.png)
![v0.10.0 theme-industrial-mobile](v0.10.0/theme-industrial-mobile.png)
![v0.10.0 theme-industrial](v0.10.0/theme-industrial.png)
![v0.10.0 theme-neutral-mobile](v0.10.0/theme-neutral-mobile.png)
![v0.10.0 theme-neutral](v0.10.0/theme-neutral.png)

## v0.11.0 · 2026-10-31 17:51 +0100 · commit `1cb329f`

**v0.11.0 — Chat sobre AI SDK y AI Elements, shell 100dvh, Sistema y Fuentes rediseñados**

Qué cambió:
- Chat con useChat y un ChatTransport propio para /ask/stream (data parts tipados, retirada del texto provisional con reset-step), Prompt Input con adjuntos, Markdown con Streamdown, traza plegable, citas numeradas que abren el fragmento, sugerencias, copiar y regenerar. Decisión por componente en ADR-010.
- Layout a 100dvh con un único scroll (el hilo), composer anclado y visor lateral u hoja inferior en móvil.
- Sistema con diagrama de piezas, estado y latencia reales (GET /health/components) y traza de la última consulta; Fuentes con tabla, filtro, detalle y cola de subida.

Qué se probó:
- mise run check OK; Playwright 77/77 tres veces, axe sin violaciones serias o críticas; 4 pruebas contra el stack real.
- 96 capturas reales (3 tamaños, 2 temas, claro y oscuro). Pendiente: teclado virtual real en móvil y facturas reales de extremo a extremo.
- Antes y después frente a v0.10.0, con el mismo stack real: evidence/comparison-v0.10-v0.11/.

![v0.11.0 ajustes-1280x720-industrial-dark](v0.11.0/ajustes-1280x720-industrial-dark.png)
![v0.11.0 ajustes-1280x720-industrial-light](v0.11.0/ajustes-1280x720-industrial-light.png)
![v0.11.0 ajustes-1280x720-neutral-dark](v0.11.0/ajustes-1280x720-neutral-dark.png)
![v0.11.0 ajustes-1280x720-neutral-light](v0.11.0/ajustes-1280x720-neutral-light.png)
![v0.11.0 ajustes-1440x900-industrial-dark](v0.11.0/ajustes-1440x900-industrial-dark.png)
![v0.11.0 ajustes-1440x900-industrial-light](v0.11.0/ajustes-1440x900-industrial-light.png)
![v0.11.0 ajustes-1440x900-neutral-dark](v0.11.0/ajustes-1440x900-neutral-dark.png)
![v0.11.0 ajustes-1440x900-neutral-light](v0.11.0/ajustes-1440x900-neutral-light.png)
![v0.11.0 ajustes-390x844-industrial-dark](v0.11.0/ajustes-390x844-industrial-dark.png)
![v0.11.0 ajustes-390x844-industrial-light](v0.11.0/ajustes-390x844-industrial-light.png)
![v0.11.0 ajustes-390x844-neutral-dark](v0.11.0/ajustes-390x844-neutral-dark.png)
![v0.11.0 ajustes-390x844-neutral-light](v0.11.0/ajustes-390x844-neutral-light.png)
![v0.11.0 chat-generando-1280x720-industrial-dark](v0.11.0/chat-generando-1280x720-industrial-dark.png)
![v0.11.0 chat-generando-1280x720-industrial-light](v0.11.0/chat-generando-1280x720-industrial-light.png)
![v0.11.0 chat-generando-1280x720-neutral-dark](v0.11.0/chat-generando-1280x720-neutral-dark.png)
![v0.11.0 chat-generando-1280x720-neutral-light](v0.11.0/chat-generando-1280x720-neutral-light.png)
![v0.11.0 chat-generando-1440x900-industrial-dark](v0.11.0/chat-generando-1440x900-industrial-dark.png)
![v0.11.0 chat-generando-1440x900-industrial-light](v0.11.0/chat-generando-1440x900-industrial-light.png)
![v0.11.0 chat-generando-1440x900-neutral-dark](v0.11.0/chat-generando-1440x900-neutral-dark.png)
![v0.11.0 chat-generando-1440x900-neutral-light](v0.11.0/chat-generando-1440x900-neutral-light.png)
![v0.11.0 chat-generando-390x844-industrial-dark](v0.11.0/chat-generando-390x844-industrial-dark.png)
![v0.11.0 chat-generando-390x844-industrial-light](v0.11.0/chat-generando-390x844-industrial-light.png)
![v0.11.0 chat-generando-390x844-neutral-dark](v0.11.0/chat-generando-390x844-neutral-dark.png)
![v0.11.0 chat-generando-390x844-neutral-light](v0.11.0/chat-generando-390x844-neutral-light.png)
![v0.11.0 chat-rechazo-1280x720-industrial-dark](v0.11.0/chat-rechazo-1280x720-industrial-dark.png)
![v0.11.0 chat-rechazo-1280x720-industrial-light](v0.11.0/chat-rechazo-1280x720-industrial-light.png)
![v0.11.0 chat-rechazo-1280x720-neutral-dark](v0.11.0/chat-rechazo-1280x720-neutral-dark.png)
![v0.11.0 chat-rechazo-1280x720-neutral-light](v0.11.0/chat-rechazo-1280x720-neutral-light.png)
![v0.11.0 chat-rechazo-1440x900-industrial-dark](v0.11.0/chat-rechazo-1440x900-industrial-dark.png)
![v0.11.0 chat-rechazo-1440x900-industrial-light](v0.11.0/chat-rechazo-1440x900-industrial-light.png)
![v0.11.0 chat-rechazo-1440x900-neutral-dark](v0.11.0/chat-rechazo-1440x900-neutral-dark.png)
![v0.11.0 chat-rechazo-1440x900-neutral-light](v0.11.0/chat-rechazo-1440x900-neutral-light.png)
![v0.11.0 chat-rechazo-390x844-industrial-dark](v0.11.0/chat-rechazo-390x844-industrial-dark.png)
![v0.11.0 chat-rechazo-390x844-industrial-light](v0.11.0/chat-rechazo-390x844-industrial-light.png)
![v0.11.0 chat-rechazo-390x844-neutral-dark](v0.11.0/chat-rechazo-390x844-neutral-dark.png)
![v0.11.0 chat-rechazo-390x844-neutral-light](v0.11.0/chat-rechazo-390x844-neutral-light.png)
![v0.11.0 chat-respuestas-1280x720-industrial-dark](v0.11.0/chat-respuestas-1280x720-industrial-dark.png)
![v0.11.0 chat-respuestas-1280x720-industrial-light](v0.11.0/chat-respuestas-1280x720-industrial-light.png)
![v0.11.0 chat-respuestas-1280x720-neutral-dark](v0.11.0/chat-respuestas-1280x720-neutral-dark.png)
![v0.11.0 chat-respuestas-1280x720-neutral-light](v0.11.0/chat-respuestas-1280x720-neutral-light.png)
![v0.11.0 chat-respuestas-1440x900-industrial-dark](v0.11.0/chat-respuestas-1440x900-industrial-dark.png)
![v0.11.0 chat-respuestas-1440x900-industrial-light](v0.11.0/chat-respuestas-1440x900-industrial-light.png)
![v0.11.0 chat-respuestas-1440x900-neutral-dark](v0.11.0/chat-respuestas-1440x900-neutral-dark.png)
![v0.11.0 chat-respuestas-1440x900-neutral-light](v0.11.0/chat-respuestas-1440x900-neutral-light.png)
![v0.11.0 chat-respuestas-390x844-industrial-dark](v0.11.0/chat-respuestas-390x844-industrial-dark.png)
![v0.11.0 chat-respuestas-390x844-industrial-light](v0.11.0/chat-respuestas-390x844-industrial-light.png)
![v0.11.0 chat-respuestas-390x844-neutral-dark](v0.11.0/chat-respuestas-390x844-neutral-dark.png)
![v0.11.0 chat-respuestas-390x844-neutral-light](v0.11.0/chat-respuestas-390x844-neutral-light.png)
![v0.11.0 chat-vacio-1280x720-industrial-dark](v0.11.0/chat-vacio-1280x720-industrial-dark.png)
![v0.11.0 chat-vacio-1280x720-industrial-light](v0.11.0/chat-vacio-1280x720-industrial-light.png)
![v0.11.0 chat-vacio-1280x720-neutral-dark](v0.11.0/chat-vacio-1280x720-neutral-dark.png)
![v0.11.0 chat-vacio-1280x720-neutral-light](v0.11.0/chat-vacio-1280x720-neutral-light.png)
![v0.11.0 chat-vacio-1440x900-industrial-dark](v0.11.0/chat-vacio-1440x900-industrial-dark.png)
![v0.11.0 chat-vacio-1440x900-industrial-light](v0.11.0/chat-vacio-1440x900-industrial-light.png)
![v0.11.0 chat-vacio-1440x900-neutral-dark](v0.11.0/chat-vacio-1440x900-neutral-dark.png)
![v0.11.0 chat-vacio-1440x900-neutral-light](v0.11.0/chat-vacio-1440x900-neutral-light.png)
![v0.11.0 chat-vacio-390x844-industrial-dark](v0.11.0/chat-vacio-390x844-industrial-dark.png)
![v0.11.0 chat-vacio-390x844-industrial-light](v0.11.0/chat-vacio-390x844-industrial-light.png)
![v0.11.0 chat-vacio-390x844-neutral-dark](v0.11.0/chat-vacio-390x844-neutral-dark.png)
![v0.11.0 chat-vacio-390x844-neutral-light](v0.11.0/chat-vacio-390x844-neutral-light.png)
![v0.11.0 chat-visor-1280x720-industrial-dark](v0.11.0/chat-visor-1280x720-industrial-dark.png)
![v0.11.0 chat-visor-1280x720-industrial-light](v0.11.0/chat-visor-1280x720-industrial-light.png)
![v0.11.0 chat-visor-1280x720-neutral-dark](v0.11.0/chat-visor-1280x720-neutral-dark.png)
![v0.11.0 chat-visor-1280x720-neutral-light](v0.11.0/chat-visor-1280x720-neutral-light.png)
![v0.11.0 chat-visor-1440x900-industrial-dark](v0.11.0/chat-visor-1440x900-industrial-dark.png)
![v0.11.0 chat-visor-1440x900-industrial-light](v0.11.0/chat-visor-1440x900-industrial-light.png)
![v0.11.0 chat-visor-1440x900-neutral-dark](v0.11.0/chat-visor-1440x900-neutral-dark.png)
![v0.11.0 chat-visor-1440x900-neutral-light](v0.11.0/chat-visor-1440x900-neutral-light.png)
![v0.11.0 chat-visor-390x844-industrial-dark](v0.11.0/chat-visor-390x844-industrial-dark.png)
![v0.11.0 chat-visor-390x844-industrial-light](v0.11.0/chat-visor-390x844-industrial-light.png)
![v0.11.0 chat-visor-390x844-neutral-dark](v0.11.0/chat-visor-390x844-neutral-dark.png)
![v0.11.0 chat-visor-390x844-neutral-light](v0.11.0/chat-visor-390x844-neutral-light.png)
![v0.11.0 fuentes-1280x720-industrial-dark](v0.11.0/fuentes-1280x720-industrial-dark.png)
![v0.11.0 fuentes-1280x720-industrial-light](v0.11.0/fuentes-1280x720-industrial-light.png)
![v0.11.0 fuentes-1280x720-neutral-dark](v0.11.0/fuentes-1280x720-neutral-dark.png)
![v0.11.0 fuentes-1280x720-neutral-light](v0.11.0/fuentes-1280x720-neutral-light.png)
![v0.11.0 fuentes-1440x900-industrial-dark](v0.11.0/fuentes-1440x900-industrial-dark.png)
![v0.11.0 fuentes-1440x900-industrial-light](v0.11.0/fuentes-1440x900-industrial-light.png)
![v0.11.0 fuentes-1440x900-neutral-dark](v0.11.0/fuentes-1440x900-neutral-dark.png)
![v0.11.0 fuentes-1440x900-neutral-light](v0.11.0/fuentes-1440x900-neutral-light.png)
![v0.11.0 fuentes-390x844-industrial-dark](v0.11.0/fuentes-390x844-industrial-dark.png)
![v0.11.0 fuentes-390x844-industrial-light](v0.11.0/fuentes-390x844-industrial-light.png)
![v0.11.0 fuentes-390x844-neutral-dark](v0.11.0/fuentes-390x844-neutral-dark.png)
![v0.11.0 fuentes-390x844-neutral-light](v0.11.0/fuentes-390x844-neutral-light.png)
![v0.11.0 sistema-1280x720-industrial-dark](v0.11.0/sistema-1280x720-industrial-dark.png)
![v0.11.0 sistema-1280x720-industrial-light](v0.11.0/sistema-1280x720-industrial-light.png)
![v0.11.0 sistema-1280x720-neutral-dark](v0.11.0/sistema-1280x720-neutral-dark.png)
![v0.11.0 sistema-1280x720-neutral-light](v0.11.0/sistema-1280x720-neutral-light.png)
![v0.11.0 sistema-1440x900-industrial-dark](v0.11.0/sistema-1440x900-industrial-dark.png)
![v0.11.0 sistema-1440x900-industrial-light](v0.11.0/sistema-1440x900-industrial-light.png)
![v0.11.0 sistema-1440x900-neutral-dark](v0.11.0/sistema-1440x900-neutral-dark.png)
![v0.11.0 sistema-1440x900-neutral-light](v0.11.0/sistema-1440x900-neutral-light.png)
![v0.11.0 sistema-390x844-industrial-dark](v0.11.0/sistema-390x844-industrial-dark.png)
![v0.11.0 sistema-390x844-industrial-light](v0.11.0/sistema-390x844-industrial-light.png)
![v0.11.0 sistema-390x844-neutral-dark](v0.11.0/sistema-390x844-neutral-dark.png)
![v0.11.0 sistema-390x844-neutral-light](v0.11.0/sistema-390x844-neutral-light.png)

## v0.12.0 · 2026-10-31 20:06 +0100 · commit `a697fc8`

**v0.12.0 — Markdown y citas correctos, citas inline, visor a pantalla completa y subida con progreso real**

Qué cambió:
- Respuestas panorámicas con Markdown válido (un constructor único, tests sobre el HTML) y solo las citas que sostienen la respuesta: «¿qué facturas tengo?» pasa de 44 citas a 5.
- Citas inline: marcadores numéricos pegados a la frase con vista previa, y «N fuentes» debajo. Asignación por reglas verificables por defecto; el modo `model` queda como opción (ADR-011).
- Visor modal a pantalla completa con zoom, arrastre, navegación entre citas y páginas, y el fragmento resaltado (GET /sources/{id}/pages/{n}/highlight). En facturas muestra el campo extraído y lo explica.
- «Añadir fuentes» con modal y aviso persistente (Sonner) con el estado real de cada archivo (SSE GET /ingest/jobs/{id}/events), errores con reintento y «Ver en Fuentes».

Qué se probó:
- mise run check OK (146 tests del servicio, 14 de scripts, contrato sin deriva); Playwright 118/118 tres veces seguidas, 4 contra el stack real; axe sin violaciones serias o críticas en rutas, temas y modos.
- gold-v2 (borrador, sin aprobar ni modificar), antes → después con `rules`: respondidas 23/33 → 24/33, no contestables rechazadas 11/11 → 11/11, sin respaldo 0 → 0, marcador inline en 24/24. Modo `model`: 26/33, 8/11 y 3 sin respaldo, por eso no es el valor por defecto.
- 152 capturas (3 tamaños, 2 temas, claro y oscuro) con fuentes sintéticas. Pendiente: región resaltada en facturas, teclado virtual real en móvil, latencia de `rules` sin otras cargas.

![v0.12.0 ajustes-1280x720-industrial-dark](v0.12.0/ajustes-1280x720-industrial-dark.png)
![v0.12.0 ajustes-1280x720-industrial-light](v0.12.0/ajustes-1280x720-industrial-light.png)
![v0.12.0 ajustes-1280x720-neutral-dark](v0.12.0/ajustes-1280x720-neutral-dark.png)
![v0.12.0 ajustes-1280x720-neutral-light](v0.12.0/ajustes-1280x720-neutral-light.png)
![v0.12.0 ajustes-1440x900-industrial-dark](v0.12.0/ajustes-1440x900-industrial-dark.png)
![v0.12.0 ajustes-1440x900-industrial-light](v0.12.0/ajustes-1440x900-industrial-light.png)
![v0.12.0 ajustes-1440x900-neutral-dark](v0.12.0/ajustes-1440x900-neutral-dark.png)
![v0.12.0 ajustes-1440x900-neutral-light](v0.12.0/ajustes-1440x900-neutral-light.png)
![v0.12.0 ajustes-390x844-industrial-dark](v0.12.0/ajustes-390x844-industrial-dark.png)
![v0.12.0 ajustes-390x844-industrial-light](v0.12.0/ajustes-390x844-industrial-light.png)
![v0.12.0 ajustes-390x844-neutral-dark](v0.12.0/ajustes-390x844-neutral-dark.png)
![v0.12.0 ajustes-390x844-neutral-light](v0.12.0/ajustes-390x844-neutral-light.png)
![v0.12.0 anadir-fuentes-1280x720-industrial-dark](v0.12.0/anadir-fuentes-1280x720-industrial-dark.png)
![v0.12.0 anadir-fuentes-1280x720-industrial-light](v0.12.0/anadir-fuentes-1280x720-industrial-light.png)
![v0.12.0 anadir-fuentes-1280x720-neutral-dark](v0.12.0/anadir-fuentes-1280x720-neutral-dark.png)
![v0.12.0 anadir-fuentes-1280x720-neutral-light](v0.12.0/anadir-fuentes-1280x720-neutral-light.png)
![v0.12.0 anadir-fuentes-1440x900-industrial-dark](v0.12.0/anadir-fuentes-1440x900-industrial-dark.png)
![v0.12.0 anadir-fuentes-1440x900-industrial-light](v0.12.0/anadir-fuentes-1440x900-industrial-light.png)
![v0.12.0 anadir-fuentes-1440x900-neutral-dark](v0.12.0/anadir-fuentes-1440x900-neutral-dark.png)
![v0.12.0 anadir-fuentes-1440x900-neutral-light](v0.12.0/anadir-fuentes-1440x900-neutral-light.png)
![v0.12.0 anadir-fuentes-390x844-industrial-dark](v0.12.0/anadir-fuentes-390x844-industrial-dark.png)
![v0.12.0 anadir-fuentes-390x844-industrial-light](v0.12.0/anadir-fuentes-390x844-industrial-light.png)
![v0.12.0 anadir-fuentes-390x844-neutral-dark](v0.12.0/anadir-fuentes-390x844-neutral-dark.png)
![v0.12.0 anadir-fuentes-390x844-neutral-light](v0.12.0/anadir-fuentes-390x844-neutral-light.png)
![v0.12.0 chat-cita-1280x720-industrial-dark](v0.12.0/chat-cita-1280x720-industrial-dark.png)
![v0.12.0 chat-cita-1280x720-industrial-light](v0.12.0/chat-cita-1280x720-industrial-light.png)
![v0.12.0 chat-cita-1280x720-neutral-dark](v0.12.0/chat-cita-1280x720-neutral-dark.png)
![v0.12.0 chat-cita-1280x720-neutral-light](v0.12.0/chat-cita-1280x720-neutral-light.png)
![v0.12.0 chat-cita-1440x900-industrial-dark](v0.12.0/chat-cita-1440x900-industrial-dark.png)
![v0.12.0 chat-cita-1440x900-industrial-light](v0.12.0/chat-cita-1440x900-industrial-light.png)
![v0.12.0 chat-cita-1440x900-neutral-dark](v0.12.0/chat-cita-1440x900-neutral-dark.png)
![v0.12.0 chat-cita-1440x900-neutral-light](v0.12.0/chat-cita-1440x900-neutral-light.png)
![v0.12.0 chat-generando-1280x720-industrial-dark](v0.12.0/chat-generando-1280x720-industrial-dark.png)
![v0.12.0 chat-generando-1280x720-industrial-light](v0.12.0/chat-generando-1280x720-industrial-light.png)
![v0.12.0 chat-generando-1280x720-neutral-dark](v0.12.0/chat-generando-1280x720-neutral-dark.png)
![v0.12.0 chat-generando-1280x720-neutral-light](v0.12.0/chat-generando-1280x720-neutral-light.png)
![v0.12.0 chat-generando-1440x900-industrial-dark](v0.12.0/chat-generando-1440x900-industrial-dark.png)
![v0.12.0 chat-generando-1440x900-industrial-light](v0.12.0/chat-generando-1440x900-industrial-light.png)
![v0.12.0 chat-generando-1440x900-neutral-dark](v0.12.0/chat-generando-1440x900-neutral-dark.png)
![v0.12.0 chat-generando-1440x900-neutral-light](v0.12.0/chat-generando-1440x900-neutral-light.png)
![v0.12.0 chat-generando-390x844-industrial-dark](v0.12.0/chat-generando-390x844-industrial-dark.png)
![v0.12.0 chat-generando-390x844-industrial-light](v0.12.0/chat-generando-390x844-industrial-light.png)
![v0.12.0 chat-generando-390x844-neutral-dark](v0.12.0/chat-generando-390x844-neutral-dark.png)
![v0.12.0 chat-generando-390x844-neutral-light](v0.12.0/chat-generando-390x844-neutral-light.png)
![v0.12.0 chat-meta-1280x720-industrial-dark](v0.12.0/chat-meta-1280x720-industrial-dark.png)
![v0.12.0 chat-meta-1280x720-industrial-light](v0.12.0/chat-meta-1280x720-industrial-light.png)
![v0.12.0 chat-meta-1280x720-neutral-dark](v0.12.0/chat-meta-1280x720-neutral-dark.png)
![v0.12.0 chat-meta-1280x720-neutral-light](v0.12.0/chat-meta-1280x720-neutral-light.png)
![v0.12.0 chat-meta-1440x900-industrial-dark](v0.12.0/chat-meta-1440x900-industrial-dark.png)
![v0.12.0 chat-meta-1440x900-industrial-light](v0.12.0/chat-meta-1440x900-industrial-light.png)
![v0.12.0 chat-meta-1440x900-neutral-dark](v0.12.0/chat-meta-1440x900-neutral-dark.png)
![v0.12.0 chat-meta-1440x900-neutral-light](v0.12.0/chat-meta-1440x900-neutral-light.png)
![v0.12.0 chat-meta-390x844-industrial-dark](v0.12.0/chat-meta-390x844-industrial-dark.png)
![v0.12.0 chat-meta-390x844-industrial-light](v0.12.0/chat-meta-390x844-industrial-light.png)
![v0.12.0 chat-meta-390x844-neutral-dark](v0.12.0/chat-meta-390x844-neutral-dark.png)
![v0.12.0 chat-meta-390x844-neutral-light](v0.12.0/chat-meta-390x844-neutral-light.png)
![v0.12.0 chat-rechazo-1280x720-industrial-dark](v0.12.0/chat-rechazo-1280x720-industrial-dark.png)
![v0.12.0 chat-rechazo-1280x720-industrial-light](v0.12.0/chat-rechazo-1280x720-industrial-light.png)
![v0.12.0 chat-rechazo-1280x720-neutral-dark](v0.12.0/chat-rechazo-1280x720-neutral-dark.png)
![v0.12.0 chat-rechazo-1280x720-neutral-light](v0.12.0/chat-rechazo-1280x720-neutral-light.png)
![v0.12.0 chat-rechazo-1440x900-industrial-dark](v0.12.0/chat-rechazo-1440x900-industrial-dark.png)
![v0.12.0 chat-rechazo-1440x900-industrial-light](v0.12.0/chat-rechazo-1440x900-industrial-light.png)
![v0.12.0 chat-rechazo-1440x900-neutral-dark](v0.12.0/chat-rechazo-1440x900-neutral-dark.png)
![v0.12.0 chat-rechazo-1440x900-neutral-light](v0.12.0/chat-rechazo-1440x900-neutral-light.png)
![v0.12.0 chat-rechazo-390x844-industrial-dark](v0.12.0/chat-rechazo-390x844-industrial-dark.png)
![v0.12.0 chat-rechazo-390x844-industrial-light](v0.12.0/chat-rechazo-390x844-industrial-light.png)
![v0.12.0 chat-rechazo-390x844-neutral-dark](v0.12.0/chat-rechazo-390x844-neutral-dark.png)
![v0.12.0 chat-rechazo-390x844-neutral-light](v0.12.0/chat-rechazo-390x844-neutral-light.png)
![v0.12.0 chat-respuestas-1280x720-industrial-dark](v0.12.0/chat-respuestas-1280x720-industrial-dark.png)
![v0.12.0 chat-respuestas-1280x720-industrial-light](v0.12.0/chat-respuestas-1280x720-industrial-light.png)
![v0.12.0 chat-respuestas-1280x720-neutral-dark](v0.12.0/chat-respuestas-1280x720-neutral-dark.png)
![v0.12.0 chat-respuestas-1280x720-neutral-light](v0.12.0/chat-respuestas-1280x720-neutral-light.png)
![v0.12.0 chat-respuestas-1440x900-industrial-dark](v0.12.0/chat-respuestas-1440x900-industrial-dark.png)
![v0.12.0 chat-respuestas-1440x900-industrial-light](v0.12.0/chat-respuestas-1440x900-industrial-light.png)
![v0.12.0 chat-respuestas-1440x900-neutral-dark](v0.12.0/chat-respuestas-1440x900-neutral-dark.png)
![v0.12.0 chat-respuestas-1440x900-neutral-light](v0.12.0/chat-respuestas-1440x900-neutral-light.png)
![v0.12.0 chat-respuestas-390x844-industrial-dark](v0.12.0/chat-respuestas-390x844-industrial-dark.png)
![v0.12.0 chat-respuestas-390x844-industrial-light](v0.12.0/chat-respuestas-390x844-industrial-light.png)
![v0.12.0 chat-respuestas-390x844-neutral-dark](v0.12.0/chat-respuestas-390x844-neutral-dark.png)
![v0.12.0 chat-respuestas-390x844-neutral-light](v0.12.0/chat-respuestas-390x844-neutral-light.png)
![v0.12.0 chat-vacio-1280x720-industrial-dark](v0.12.0/chat-vacio-1280x720-industrial-dark.png)
![v0.12.0 chat-vacio-1280x720-industrial-light](v0.12.0/chat-vacio-1280x720-industrial-light.png)
![v0.12.0 chat-vacio-1280x720-neutral-dark](v0.12.0/chat-vacio-1280x720-neutral-dark.png)
![v0.12.0 chat-vacio-1280x720-neutral-light](v0.12.0/chat-vacio-1280x720-neutral-light.png)
![v0.12.0 chat-vacio-1440x900-industrial-dark](v0.12.0/chat-vacio-1440x900-industrial-dark.png)
![v0.12.0 chat-vacio-1440x900-industrial-light](v0.12.0/chat-vacio-1440x900-industrial-light.png)
![v0.12.0 chat-vacio-1440x900-neutral-dark](v0.12.0/chat-vacio-1440x900-neutral-dark.png)
![v0.12.0 chat-vacio-1440x900-neutral-light](v0.12.0/chat-vacio-1440x900-neutral-light.png)
![v0.12.0 chat-vacio-390x844-industrial-dark](v0.12.0/chat-vacio-390x844-industrial-dark.png)
![v0.12.0 chat-vacio-390x844-industrial-light](v0.12.0/chat-vacio-390x844-industrial-light.png)
![v0.12.0 chat-vacio-390x844-neutral-dark](v0.12.0/chat-vacio-390x844-neutral-dark.png)
![v0.12.0 chat-vacio-390x844-neutral-light](v0.12.0/chat-vacio-390x844-neutral-light.png)
![v0.12.0 chat-visor-1280x720-industrial-dark](v0.12.0/chat-visor-1280x720-industrial-dark.png)
![v0.12.0 chat-visor-1280x720-industrial-light](v0.12.0/chat-visor-1280x720-industrial-light.png)
![v0.12.0 chat-visor-1280x720-neutral-dark](v0.12.0/chat-visor-1280x720-neutral-dark.png)
![v0.12.0 chat-visor-1280x720-neutral-light](v0.12.0/chat-visor-1280x720-neutral-light.png)
![v0.12.0 chat-visor-1440x900-industrial-dark](v0.12.0/chat-visor-1440x900-industrial-dark.png)
![v0.12.0 chat-visor-1440x900-industrial-light](v0.12.0/chat-visor-1440x900-industrial-light.png)
![v0.12.0 chat-visor-1440x900-neutral-dark](v0.12.0/chat-visor-1440x900-neutral-dark.png)
![v0.12.0 chat-visor-1440x900-neutral-light](v0.12.0/chat-visor-1440x900-neutral-light.png)
![v0.12.0 chat-visor-390x844-industrial-dark](v0.12.0/chat-visor-390x844-industrial-dark.png)
![v0.12.0 chat-visor-390x844-industrial-light](v0.12.0/chat-visor-390x844-industrial-light.png)
![v0.12.0 chat-visor-390x844-neutral-dark](v0.12.0/chat-visor-390x844-neutral-dark.png)
![v0.12.0 chat-visor-390x844-neutral-light](v0.12.0/chat-visor-390x844-neutral-light.png)
![v0.12.0 chat-visor-factura-1280x720-industrial-dark](v0.12.0/chat-visor-factura-1280x720-industrial-dark.png)
![v0.12.0 chat-visor-factura-1280x720-industrial-light](v0.12.0/chat-visor-factura-1280x720-industrial-light.png)
![v0.12.0 chat-visor-factura-1280x720-neutral-dark](v0.12.0/chat-visor-factura-1280x720-neutral-dark.png)
![v0.12.0 chat-visor-factura-1280x720-neutral-light](v0.12.0/chat-visor-factura-1280x720-neutral-light.png)
![v0.12.0 chat-visor-factura-1440x900-industrial-dark](v0.12.0/chat-visor-factura-1440x900-industrial-dark.png)
![v0.12.0 chat-visor-factura-1440x900-industrial-light](v0.12.0/chat-visor-factura-1440x900-industrial-light.png)
![v0.12.0 chat-visor-factura-1440x900-neutral-dark](v0.12.0/chat-visor-factura-1440x900-neutral-dark.png)
![v0.12.0 chat-visor-factura-1440x900-neutral-light](v0.12.0/chat-visor-factura-1440x900-neutral-light.png)
![v0.12.0 chat-visor-factura-390x844-industrial-dark](v0.12.0/chat-visor-factura-390x844-industrial-dark.png)
![v0.12.0 chat-visor-factura-390x844-industrial-light](v0.12.0/chat-visor-factura-390x844-industrial-light.png)
![v0.12.0 chat-visor-factura-390x844-neutral-dark](v0.12.0/chat-visor-factura-390x844-neutral-dark.png)
![v0.12.0 chat-visor-factura-390x844-neutral-light](v0.12.0/chat-visor-factura-390x844-neutral-light.png)
![v0.12.0 fuentes-1280x720-industrial-dark](v0.12.0/fuentes-1280x720-industrial-dark.png)
![v0.12.0 fuentes-1280x720-industrial-light](v0.12.0/fuentes-1280x720-industrial-light.png)
![v0.12.0 fuentes-1280x720-neutral-dark](v0.12.0/fuentes-1280x720-neutral-dark.png)
![v0.12.0 fuentes-1280x720-neutral-light](v0.12.0/fuentes-1280x720-neutral-light.png)
![v0.12.0 fuentes-1440x900-industrial-dark](v0.12.0/fuentes-1440x900-industrial-dark.png)
![v0.12.0 fuentes-1440x900-industrial-light](v0.12.0/fuentes-1440x900-industrial-light.png)
![v0.12.0 fuentes-1440x900-neutral-dark](v0.12.0/fuentes-1440x900-neutral-dark.png)
![v0.12.0 fuentes-1440x900-neutral-light](v0.12.0/fuentes-1440x900-neutral-light.png)
![v0.12.0 fuentes-390x844-industrial-dark](v0.12.0/fuentes-390x844-industrial-dark.png)
![v0.12.0 fuentes-390x844-industrial-light](v0.12.0/fuentes-390x844-industrial-light.png)
![v0.12.0 fuentes-390x844-neutral-dark](v0.12.0/fuentes-390x844-neutral-dark.png)
![v0.12.0 fuentes-390x844-neutral-light](v0.12.0/fuentes-390x844-neutral-light.png)
![v0.12.0 sistema-1280x720-industrial-dark](v0.12.0/sistema-1280x720-industrial-dark.png)
![v0.12.0 sistema-1280x720-industrial-light](v0.12.0/sistema-1280x720-industrial-light.png)
![v0.12.0 sistema-1280x720-neutral-dark](v0.12.0/sistema-1280x720-neutral-dark.png)
![v0.12.0 sistema-1280x720-neutral-light](v0.12.0/sistema-1280x720-neutral-light.png)
![v0.12.0 sistema-1440x900-industrial-dark](v0.12.0/sistema-1440x900-industrial-dark.png)
![v0.12.0 sistema-1440x900-industrial-light](v0.12.0/sistema-1440x900-industrial-light.png)
![v0.12.0 sistema-1440x900-neutral-dark](v0.12.0/sistema-1440x900-neutral-dark.png)
![v0.12.0 sistema-1440x900-neutral-light](v0.12.0/sistema-1440x900-neutral-light.png)
![v0.12.0 sistema-390x844-industrial-dark](v0.12.0/sistema-390x844-industrial-dark.png)
![v0.12.0 sistema-390x844-industrial-light](v0.12.0/sistema-390x844-industrial-light.png)
![v0.12.0 sistema-390x844-neutral-dark](v0.12.0/sistema-390x844-neutral-dark.png)
![v0.12.0 sistema-390x844-neutral-light](v0.12.0/sistema-390x844-neutral-light.png)
![v0.12.0 subida-aviso-1280x720-industrial-dark](v0.12.0/subida-aviso-1280x720-industrial-dark.png)
![v0.12.0 subida-aviso-1280x720-industrial-light](v0.12.0/subida-aviso-1280x720-industrial-light.png)
![v0.12.0 subida-aviso-1280x720-neutral-dark](v0.12.0/subida-aviso-1280x720-neutral-dark.png)
![v0.12.0 subida-aviso-1280x720-neutral-light](v0.12.0/subida-aviso-1280x720-neutral-light.png)
![v0.12.0 subida-aviso-1440x900-industrial-dark](v0.12.0/subida-aviso-1440x900-industrial-dark.png)
![v0.12.0 subida-aviso-1440x900-industrial-light](v0.12.0/subida-aviso-1440x900-industrial-light.png)
![v0.12.0 subida-aviso-1440x900-neutral-dark](v0.12.0/subida-aviso-1440x900-neutral-dark.png)
![v0.12.0 subida-aviso-1440x900-neutral-light](v0.12.0/subida-aviso-1440x900-neutral-light.png)
![v0.12.0 subida-aviso-390x844-industrial-dark](v0.12.0/subida-aviso-390x844-industrial-dark.png)
![v0.12.0 subida-aviso-390x844-industrial-light](v0.12.0/subida-aviso-390x844-industrial-light.png)
![v0.12.0 subida-aviso-390x844-neutral-dark](v0.12.0/subida-aviso-390x844-neutral-dark.png)
![v0.12.0 subida-aviso-390x844-neutral-light](v0.12.0/subida-aviso-390x844-neutral-light.png)

## v0.13.0 · integración sobre v0.12.0

La versión integrada conserva las citas inline, el visor y la subida con progreso de v0.12.0 (ADR-011), y añade las consultas de facturas con plan v2, SQL generado en código y aclaraciones (ADR-012). El tag `v0.13.0-pre-merge` conserva la revisión original de facturas `9b6552a`; `v0.13.0` identifica la fusión validada.

Las capturas con facturas reales de esta integración son locales y no se publican. Las galerías anteriores mantienen las capturas sintéticas de sus tags.
