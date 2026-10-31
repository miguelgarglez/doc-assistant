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

## 14:35 · Paquete completo probado y revisión #13/#14/#19/#23 (v0.7.0)
- `mise run package --smoke real`: ZIP de 4,09 GB (191 ficheros + 3 binarios + 3 modelos) en 9 s; en una carpeta temporal limpia: setup sin descargas (19 s), arranque, PDF subido, "¿Qué alcance tiene el sensor?" → "4 m" con cita (3 s), factura sintética subida y extraída (24 s), puertos 3000/8000/8081–8083 liberados; total 72 s (1:24 con el empaquetado).
- Licencias revisadas en las fichas: Qwen3.5-4B Apache-2.0, bge-m3 MIT, bge-reranker-v2-m3 Apache-2.0, llama.cpp MIT; textos añadidos en `licenses/` (los repos BAAI no publican fichero LICENSE).
- #14, #23 y #19 resueltos con tests; #13 parcial (aviso claro), lo demás depende del runtime OCR.
- Qué se probó: `mise run check` → OK; e2e → 12 passed; test de #14 falla con el código anterior.
- Decisión clave y por qué: avisar en vez de instalar Ollama, porque el runtime OCR está aún por decidir.

## 15:00 · OCR dentro del ZIP: GLM-OCR GGUF en llama-server (v0.8.0)
- Descarga (14:24): `GLM-OCR-Q8_0.gguf` y `mmproj-GLM-OCR-Q8_0.gguf` de ggml-org/GLM-OCR-GGUF, fijados por commit y SHA256 en `assets.json`; `setup` los baja y `package` los mete en `models/`.
- Medición con el LLM cargado (6 facturas sintéticas): llama.cpp 72/72 campos, 6/6 ok, ~22 s/factura, ~2,3–2,7 GB de RAM pico del servidor OCR; Ollama glm-ocr 72/72, 6/6 ok, 27–36 s/factura. Ajustes: `-c 8192 --flash-attn on --image-max-tokens 1600` (sin ellos, error de memoria de Metal junto al LLM).
- `start` arranca el OCR en :8084; Ollama queda como alternativa (`DOC_ASSISTANT_OCR_RUNTIME=ollama`). Setup/start avisan si faltan los GGUF (#13 resuelto).
- Arreglo del parser de importes: tipo entre paréntesis ("IVA (21%)", "IRPF (-15%)"), base sin tipo y "TOTAL FACTURA". En facturas reales fuera del repo (solo agregado) el estado ok pasó de 0/5 a 5/5.
- Qué se probó: `mise run check` → OK (60 tests servicio + scripts); e2e → 12 passed; `mise run package --smoke real` → ZIP 5,53 GB, OCR en :8084 desde `models/` del ZIP, factura extraída (14 s), puertos 3000/8000/8081–8084 liberados.
- Decisión clave y por qué: un solo runtime (llama.cpp) y nada que descargar al evaluar; la licencia de los GGUF no está declarada en su ficha y se cita la MIT del modelo base (duda anotada en NOTICE).

## 15:58 · Sistema de diseño y experiencia de consulta (v0.9.0)
- Temas industrial y neutral, modo claro y oscuro, atajos, historial, copia, cancelación, cargas y visor. Revisión de accesibilidad aplicada.
- Probado: `mise run check` correcto y 38 pruebas e2e en tres pasadas.

## v0.10.0 · Chat, fuentes y sistema
- Chat acumulado con SSE, texto provisional y pasos; navegación separada para Fuentes, Ajustes y Sistema. El catálogo permite revisar páginas y fragmentos.
- El estado por pieza queda sin medir si el servicio no ofrece el endpoint; la propuesta está en el contrato compartido.
- Probado: `mise run check` correcto (88 tests del servicio y 14 de scripts); 69 pruebas Playwright en tres pasadas, con axe en chat, fuentes, ajustes y sistema × dos temas × claro/oscuro.

## Cierre v0.10.0 · streaming y panorámicas
- Incorporadas las mejoras del servicio y el ADR-009. Una prueba en vivo con FastAPI y eventos espaciados comprobó que el proxy entrega los eventos de forma incremental. Un rechazo con `retract:true` sustituye el texto provisional antes de `done`.

## 17:50 · Chat sobre AI SDK, shell a 100dvh, Sistema y Fuentes rediseñados (v0.11.0)
- Qué cambió: el chat usa `useChat` con un `ChatTransport` propio sobre `/ask/stream` y componentes de AI Elements adaptados a Base UI (ADR-010); el shell ocupa `100dvh` con un único scroll; Sistema dibuja las piezas con estado y latencia (`GET /health/components`) y la traza de la última consulta; Fuentes es una tabla con filtro, detalle lateral y cola de subida.
- Qué se probó (17:41–17:50): `mise run check` → OK (eslint sin errores, tsc, build, 90 tests del servicio, 14 de scripts, contrato sin deriva); Playwright 77 pasadas de 77, tres veces seguidas, con axe en todas las rutas, temas y modos; 4 pruebas contra el stack real (`LIVE_BASE_URL`) → correctas; 96 capturas reales en `evidence/screenshots` (1440x900, 1280x720, 390x844 × industrial/neutral × claro/oscuro: vacío, respuestas, rechazo, visor, Fuentes, Sistema, Ajustes, generación en curso), revisadas una a una por muestreo.
- Un fallo no reproducido: en una pasada lanzada a la vez que las capturas reales (CPU saturada) fallaron dos pruebas de Sistema por tiempo; sin carga, 77/77 tres veces.
- Decisión clave y por qué: las citas se muestran como píldoras tras la respuesta y una lista de fuentes plegable, no por frase, porque el verificador valida la respuesta entera y alinear frases con fragmentos sería una heurística sin base.
- Pendiente: teclado virtual real en móvil, facturas reales de extremo a extremo en la nueva Fuentes (solo con respuestas simuladas), citas por frase.

## 21:00 · Facturas con plan validado y resolución en código (v0.13.0)
- Qué cambió: ver ADR-011. El LLM solo propone la intención y las pistas. Personas, números, roles, años y campos se resuelven en código sobre tablas derivadas tipadas. La ambigüedad se resuelve preguntando.
- Qué se probó:
  - 155 tests (ruff y mypy limpios).
  - Baterías con LLM real en puertos aislados: A 36/36 y B 33/33, sin respuestas falsas; v0.11 sobre las mismas: 6/36 y 7/33, con 11 falsas en total.
  - Índice de 2.005 facturas: 10 correctas y 5 aclaraciones legítimas, con p50 1,6 s en la vía de facturas y 33 ms en la parte determinista.
  - Migración sobre una copia del índice: 35 ms la primera vez, 5 ms después, sin tocar `facturas`.
- Decisión clave y por qué: el año, el rol y los campos salen de la pregunta, porque el modelo de 4B inventaba años y omitía campos. Preguntar es mejor que elegir una factura al azar.
- Pendiente: un gold aprobado, pistas en otros idiomas y triggers de cambios para índices muy grandes.

