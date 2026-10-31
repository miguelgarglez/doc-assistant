# CHECKPOINT
(Horas reales de los commits, Europe/Madrid, tomadas de `git log`.)

## Hitos
- **31-oct 12:11 · Estructura creada** (commit 2ed6516). Monorepo con dos piezas: servicio de IA en Python y web en Next.js.
  - Qué se probó: `uv`, `node`, `pnpm`, `llama-server` presentes (`which` + versiones) → OK, sin instalar nada.
  - Decisión clave y por qué: dos servicios separados por un contrato OpenAPI; la IA puede cambiar o escalar sin tocar la web (ADR-001).
- **31-oct 12:24 · Servicio IA y web base unidos** (4d8af04, merges 233c0cd/b88ce06, arreglo 51df8a2 12:25). Codex migró el núcleo del slice a FastAPI; Cursor montó la web con shadcn sobre Base UI y los 6 componentes de dominio con datos de ejemplo.
  - Qué se probó: `ruff` OK, `mypy src` "no issues in 11 files", `pytest` 29 passed; `pnpm lint`, `typecheck`, `build` OK tras arreglos.
  - Decisión clave y por qué: quité el paquete npm ajeno `cn` que metió el ayudante y lo sustituí por la utilidad estándar de shadcn (ADR-005). Ojo: 29 tests frente a 81 del slice, pendiente de auditar.
- **31-oct 12:30 · Arranque unificado verificado** (5ede52f). `mise run start` levanta 3 llama-server, el servicio IA y la web, en orden y con comprobación de salud.
  - Qué se probó: `mise run start` + Ctrl-C (SIGINT) → "todos los procesos cerrados" en ~1 s; `lsof` puertos 8081-8083/8000/3000 libres; `pgrep` sin huérfanos (con modelos reales y con `DOC_ASSISTANT_FAKE_LLAMA=1`). Puerto ocupado → mensaje claro y código 2. `mise run setup` descargó llama.cpp b12020 y su SHA256 coincidió.
  - Decisión clave y por qué: mise + scripts Python sin shell, porque es lo único que funciona igual en Mac, Linux y Windows sin Docker (ADR-003/004). Windows preparado (CI escrito, no ejecutado), no probado.
- **31-oct 12:32 · Contrato y check** (e9ca554). `openapi.json` sale del servicio; los tipos TS se generan de él.
  - Qué se probó: `mise run check` → "[check] OK" (ruff, mypy, 29 tests, contrato sin drift, eslint, tsc, next build).
  - Decisión clave y por qué: si el contrato y los tipos TS se desincronizan, el check falla; así la web nunca usa un API que no existe.
- **31-oct 12:40 · Primera pregunta real extremo a extremo** (a través del proxy de Next, con los PDFs de prueba, sin commitearlos).
  - Qué se probó: `POST /api/ingest` (4 PDFs) → 44 fragmentos en 1,8 s. pregunta de especificación sobre un datasheet → valor correcto con cita de sección y página, 7 s. "¿Cuánto cuesta…?" → rechazo "No dispongo de esa información", 5 s. `GET /api/sources/DOC-A/pages/1` → 200 image/png.
  - Decisión clave y por qué: el LLM arranca con `--reasoning-budget 0`; sin eso Qwen "piensa" y cada pregunta caducaba a los 90 s. Es una prueba de humo con 2 preguntas, no una evaluación.
- **31-oct 12:48 · Setup no redescarga modelos** (prioridad de Miguel). La carpeta de modelos se resuelve en este orden: `--models-dir` > `DOC_ASSISTANT_MODELS_DIR` > `.env.local` > `./models`. Setup guarda la ruta elegida en `.env.local`.
  - Qué se probó: `mise run setup --models-dir <carpeta de modelos> --verify` → 3 modelos "SHA256 verificado", "no hay nada que descargar", ruta guardada en `.env.local`. Después `mise run start` sin variables → "modelos: … (origen: .env.local)", todo OK; Ctrl-C → puertos libres. 5 tests nuevos del orden de resolución (verdes). El `.part` de 417 MB de la descarga parada está en `_trash/` (no se ha borrado).
  - Decisión clave y por qué: solo se descarga lo que falta, con reanudación, y pide confirmación si son más de 1 GB (`--yes` en CI), para que nadie se baje 4 GB por error. Comando para tu Mac: una vez `DOC_ASSISTANT_MODELS_DIR=<carpeta de modelos> mise run setup`; después solo `mise run start`.
- **31-oct 12:47 · Página conectada al API real** (fusionado feat/web-phase2). Cliente tipado generado del contrato; pregunta → respuesta con citas; al pulsar una cita se abre la página y el fragmento resaltado; rechazo y error visibles.
  - Qué se probó: `mise run check` → OK; `pnpm e2e` → 3 passed (respuesta con fuente, rechazo, error) y las 3 capturas de `evidence/screenshots/` salen idénticas al regenerarlas (git sin cambios).
  - Decisión clave y por qué: los tests de UI usan respuestas simuladas del API (no modelos), para que las capturas sean reproducibles en cualquier máquina. Pendiente: los textos hablaban de "revisión fiscal" y la tipografía era toda monoespaciada; se está corrigiendo (agente 06).

## Sigue
1. Auditar 29 vs 81 tests del slice. 2. Conectar la página al API real con cliente tipado (openapi-fetch). 3. Facturas (subida, extracción con nulos, InvoiceReviewCard). 4. Revisión independiente (gpt-6.1-sol). 5. architecture.md / scaling-deployment.md / evidence/.

## Comandos
`mise install && DOC_ASSISTANT_MODELS_DIR=<carpeta de modelos> mise run setup` · `mise run start` · `mise run check` · `DOC_ASSISTANT_FAKE_LLAMA=1 mise run start` (sin modelos)
- Ficheros de agentes: prompts/logs en `_agents/` (git-ignorado); worktrees fusionados movidos a `_trash/agents/` (no borrados). El worktree tt-ai se eliminó con `git worktree remove` a las 12:41 (estaba fusionado y limpio).

## 13:16 — Python fase 2 y pulido web fusionados; smoke real de facturas
Se fusionaron feat/py-phase2 (auditoría 81 tests: 26 migrados, 55 excluidos a propósito por ser de evaluación, 0 perdidos; `POST /documents`; facturas PD-8/PD-14 con OCR GLM, puertas y SQL en `/ask`) y feat/web-polish (dominio "título del producto", visor lado a lado, navegación de citas, estados, capturas desktop/móvil). `check` detectó deriva del contrato y se regeneró el cliente. Se corrigieron dos fallos: las variables de fuente se referenciaban a sí mismas y el e2e forzaba Courier (la UI salía en monoespaciada); y el proxy reenviaba `Expect: 100-continue`, rompiendo subidas de >1 KB con undici.
Qué se probó: `mise run check` → exit 0 (42 + 5 tests); `pnpm e2e` → 6 passed, capturas estables (md5 igual en dos ejecuciones). Stack real: subida de 2 PDFs sintéticos y 6 facturas sintéticas → 6/6 estado ok, 0 discrepancias en número, base, IVA, IRPF y total frente al JSON (~28 s/factura). "Importe total de F-2026-001" → 537.94 con cita SQL; "rango del sensor" → "4 m" verificado; "precio del robot" → rechazo. Limitaciones: "suma del IVA de todas" se rechaza (el plan no agrega); `fecha_emision` sale como 01/01/2026, sin normalizar a ISO.
Decisión clave y por qué: el proxy filtra hop-by-hop + Expect y devuelve 502 `{code,message}`, para que el cliente tipado siempre reciba el contrato de error, incluso si el servicio cae.

## 13:33 · Revisión aplicada, facturas en la web, empaquetado y evidencia (v0.5.0)
- Revisión independiente (gpt-6.1-sol, 25 hallazgos) triada en ADR-006; aplicados los de seguridad/robustez del API y del proxy (límites de subida, confinamiento, allowlist de cabeceras, doc_id opaco, transacción de facturas). UI de facturas (pestañas, subida, InvoiceReviewCard). `mise run package` (ZIP64 con modelos, binarios llama b12020 de 3 plataformas, NOTICE). `mise run evidence [--live]`, galería `evidence/evolution/`, tags v0.1.0–v0.4.0, CHANGELOG y regla de versionado.
- La corrida live detectó un índice SQLite antiguo sin la columna `display_doc` → 500. Ahora el esquema lleva `PRAGMA user_version` y un índice de otra versión se aparta a `.bak` (no se borra) y se recrea.
- Qué se probó: `mise run check` → OK (55 + 7 tests); `pnpm e2e` → 11 passed (13:28); `mise run evidence --live --no-screenshots` (13:30) → 6/6 facturas ok sin discrepancias (11–18 s), 2 preguntas de documento con cita, total 537.94 con cita, 2 rechazos; puertos libres después. `mise run package --no-models --smoke fake` → OK (antes de la ronda 2; pendiente repetir y la corrida con modelos).
- Decisión clave y por qué: un índice es derivado (se reconstruye reingestando), así que versionarlo y apartarlo es más simple y seguro que escribir migraciones.

## 13:42 · Nombre público doc-assistant y documentación para Miguel (v0.6.0)
- Renombrado a `doc-assistant`: paquete `doc_assistant`, variables `DOC_ASSISTANT_*` (`.env.local` actualizado), título de la UI "Doc Assistant", fixture e2e neutra (ACME-DEMO-DS, creada desde HTML en `e2e/fixtures/src`), pie de página genérico en el troceado. Se quitaron de los docs las referencias a documentos y valores del kit. `.DS_Store` deja de versionarse.
- Nuevos: `docs/requirements-coverage.md` (17 cumplidas, 10 parciales, 4 no), `docs/open-gaps.md` y el escalado a toda la empresa en `scaling-deployment.md`, con las costuras propuestas sin aplicar.
- Auditoría para publicar: ningún fichero del kit está en el historial (SHA256 comparados: 0 coincidencias), ni modelos, binarios, `.env` o secretos. Pero los commits anteriores contienen el nombre de la empresa y, en el CHECKPOINT de 12:40, un id de documento y un valor del kit → **no se publica** sin reescribir la historia (pendiente de Miguel).
- Qué se probó: `mise run check` → OK; `mise run evidence` → 11 passed, capturas regeneradas.
- Decisión clave y por qué: renombrar en HEAD es reversible; reescribir la historia, no. Por eso queda para Miguel.

## 14:05 · Historial reescrito y auditado para publicar (v0.6.1)
- Copia completa antes (bundle + mirror + snapshot del árbol fuera del repo, nada borrado). Reescritura con git-filter-repo en un clon aparte: nombres y rutas al nombre público, líneas con id/valor de documento del kit neutralizadas, fixture antigua y `.DS_Store` fuera, y las capturas de cada commit regeneradas ejecutando el e2e de ese mismo commit (30 imágenes). Los tags v0.1.0–v0.6.0 se recrearon en los commits equivalentes. El repo local se alineó con `reset` (rama `pre-rewrite/main` y tags `pre-rewrite/*` solo locales).
- Qué se probó: auditoría de publicación (kit por SHA256, patrones en contenido/rutas/mensajes, emails, gitleaks, binarios) → 0 hallazgos; control positivo sobre la copia antigua → 194. `mise run check` → OK; e2e → 11 passed.
- Decisión clave y por qué: reescribir en un clon y alinear al final deja el original intacto en la copia si algo falla.
