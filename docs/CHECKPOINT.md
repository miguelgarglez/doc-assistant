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
- **31-oct 12:32 · Contrato y check** (4588e84). `openapi.json` sale del servicio; los tipos TS se generan de él.
  - Qué se probó: `mise run check` → "[check] OK" (ruff, mypy, 29 tests, contrato sin drift, eslint, tsc, next build).
  - Decisión clave y por qué: si el contrato y los tipos TS se desincronizan, el check falla; así la web nunca usa un API que no existe.
- **31-oct 12:40 · Primera pregunta real extremo a extremo** (a través del proxy de Next, con PDFs de prueba, sin commitearlos).
  - Qué se probó: `POST /api/ingest` (4 PDFs) → 44 fragmentos en 1,8 s. "¿Carga útil máxima del DOC-A?" → "N kg", cita DOC-A §2.1 p.1, fragmento literal, 7 s. "¿Cuánto cuesta…?" → rechazo "No dispongo de esa información", 5 s. `GET /api/sources/DOC-A/pages/1` → 200 image/png.
  - Decisión clave y por qué: el LLM arranca con `--reasoning-budget 0`; sin eso Qwen "piensa" y cada pregunta caducaba a los 90 s. Es una prueba de humo con 2 preguntas, no una evaluación.
- **31-oct 12:48 · Setup no redescarga modelos** (prioridad de Miguel). La carpeta de modelos se resuelve en este orden: `--models-dir` > `DOC_ASSISTANT_MODELS_DIR` > `.env.local` > `./models`. Setup guarda la ruta elegida en `.env.local`.
  - Qué se probó: `mise run setup --models-dir <carpeta de modelos> --verify` → 3 modelos "SHA256 verificado", "no hay nada que descargar", ruta guardada en `.env.local`. Después `mise run start` sin variables → "modelos: … (origen: .env.local)", todo OK; Ctrl-C → puertos libres. 5 tests nuevos del orden de resolución (verdes). El `.part` de 417 MB de la descarga parada está en `_trash/` (no se ha borrado).
  - Decisión clave y por qué: solo se descarga lo que falta, con reanudación, y pide confirmación si son más de 1 GB (`--yes` en CI), para que nadie se baje 4 GB por error. Comando para tu Mac: una vez `DOC_ASSISTANT_MODELS_DIR=<carpeta de modelos> mise run setup`; después solo `mise run start`.

## Sigue
1. Auditar 29 vs 81 tests del slice. 2. Conectar la página al API real con cliente tipado (openapi-fetch). 3. Facturas (subida, extracción con nulos, InvoiceReviewCard). 4. Revisión independiente (gpt-6.1-sol). 5. architecture.md / scaling-deployment.md / evidence/.

## Comandos
`mise install && DOC_ASSISTANT_MODELS_DIR=<carpeta de modelos> mise run setup` · `mise run start` · `mise run check` · `DOC_ASSISTANT_FAKE_LLAMA=1 mise run start` (sin modelos)
