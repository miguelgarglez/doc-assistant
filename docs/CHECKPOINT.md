# CHECKPOINT

## Estado de un vistazo

- Candidato v0.16.0 desde main v0.15.3: identificadores de petición, trazas opcionales y almacén interno.
- Check completo, tres pasadas e2e con axe y cuatro casos de humo HTTP con modelos reales correctos; auditoría del commit final en el registro privado de integración.
- Cobertura: 18 cumplidas, 10 parciales y 3 no, según `requirements-coverage.md`.
- ADR-014 implementa bloques con evidencia y alternativa Markdown.
- Consultas limitadas por proceso a dos activas y cuatro en espera, hasta 60 segundos.
- La cola no limita ingestas ni comparte capacidad entre procesos.
- La evaluación sintética tras corregir importes obtuvo 11 coincidencias de 12 con un oráculo limitado.
- Falta gold aprobado y evaluación representativa; no hay una tasa general de error acreditada.
- Faltan carga sostenida, equidad de cola y causa demostrada del error histórico sin traza.
- Linux y Windows no están probados. El check de integración pasa en macOS ARM64 con dependencias locales desde lockfiles, sin ampliar la raíz del build.
- Historial y feedback tienen piezas internas probadas en la rama de origen, desconectadas de la API y de la interfaz. Multiusuario sigue como propuesta.
- No hay persistencia automática; faltan privacidad, retención, autorización y comunicación de errores de escritura.

## Diario de integración v0.16.0

- 01-Nov 12:17 CET: validación local completa tras autorizar dependencias desde lockfiles. Corregido el formato de imports de una prueba. Check: 369 pruebas del servicio, 35 live omitidas y 26 de scripts; lint, tipos, contrato sin deriva y build correctos.
- Tres pasadas Playwright con axe y Node 24.22.2: 183 aprobadas y cuatro live omitidas cada una. Humo HTTP vía proxy con documento citado, factura, aclaración y rechazo correctos, incluida correlación de petición. OCR comprobado por health, sin repetir ingesta. Procesos propios cerrados por PID. Sin cambios visuales.

- 01-Nov 12:02 CET: integrados los 66 commits posteriores a v0.15.2 mediante merge. Conservado el índice docs/README.md y el diario previo de main.
- Corregida una expectativa del test SSE importado. La reproducción con Node 24.22.2 falló antes y pasó después; añadido caso con request_id dentro del JSON. No sustituye Playwright.
- Comparación OpenAPI con main: solo se añade request_id a DoneEvent y a sus campos de salida requeridos. La regeneración y el check de deriva pasan en la continuación.
- Enlaces internos: 692 comprobados, 0 rotos. Búsqueda del nombre privado sin coincidencias. Auditoría preliminar del merge y tags existentes: TOTAL 0.
- La validación pendiente del primer pase queda resuelta por la continuación de las 12:17 CET. No hay cambios visuales ni capturas nuevas.
- No se han activado los endpoints de historial ni feedback. No se ha creado tag ni actualizado main.

## Hitos
- **01-Nov 02:51 · Suite del servicio.** 314 pruebas pasan y 35 live se omiten con el entorno Python existente. La regresión se ha ajustado a Ruff. No sustituye `mise run check` ni las tres pasadas e2e.
- **01-Nov 02:50 · Carga sintética concurrente.** Con modelos locales, cuatro consultas SSE y dos ingestas PDF simultáneas terminaron correctamente. El modelo tenía dos slots; esta muestra no demuestra el comportamiento bajo saturación prolongada.
- **01-Nov 02:49 · Conexión SQLite en SSE.** Una prueba alterna dos hilos y reproducía `internal_error`. La búsqueda cierra su conexión antes del siguiente evento y reutiliza los fragmentos para las citas. 35 pruebas de streaming y consulta pasan; falta carga real concurrente y cierre de versión.
- **01-nov 02:40 · Recorrido del ZIP.** macOS ARM64, b12020 y cinco modelos con SHA256 correcto. Cuatro PDF (44 fragmentos) y cinco facturas procesados. La consulta documental con cita y visor, la factura, la aclaración y el rechazo funcionaron en serie. Una consulta documental concurrente mostró antes un error interno de causa no determinada. Las capturas y datos reales permanecen fuera del repo. Tres pasadas anteriores de Playwright con axe y `mise run check` pasaron; cuatro pruebas live se omitieron por pasada.
- **01-nov 02:32 · Auditoría preliminar actualizada.** Clon limpio de `258dda3`: TOTAL 0. No hay tag v0.15.0 y esta comprobación no sustituye la auditoría de entrega.
- **01-nov 02:31 · Repetición del experimento y checklist.** El comando publicado de comparación de modelos se ejecutó desde el repositorio y reprodujo las respuestas; la RSS varió entre ejecuciones. Checklist de shadcn consultado: sin componentes añadidos, sin `next/image`; lint, tipos y Playwright pasaron.
- **01-nov 02:31 · Verificación visual sintética.** Tres parejas de capturas a 1440 × 900 en `evidence/comparison-v0.14.0-continuacion/`; antes de la galería v0.14.0, después de la rama actual. Cada pareja es idéntica byte a byte y se inspeccionó. No cubre datos reales ni otros tamaños o temas.
- **01-nov 02:31 · Playwright con versiones fijadas.** Tres pasadas con Node 24.22.2: 180 aprobadas y 4 live omitidas cada una; incluyen axe. El puerto 3180 quedó libre.
- **01-nov 02:28 · Comparación exploratoria de modelos.** Qwen3.5 4B y 9B respondieron tres preguntas sintéticas iguales; se anotaron RSS y tiempos individuales con otra actividad en el equipo. Método reproducible y límites en `modelos-hardware.md`; no permite descartar alternativas. Los dos procesos se cerraron por PID.
- **01-nov 02:27 · Documentación de continuación.** CHANGELOG y cobertura reflejan la comparación sintética, las muestras de memoria y los límites de las verificaciones, sin declarar una versión cerrada.
- **01-nov 02:27 · Memoria de modelos.** Cuatro servidores con compilación 11960 y modelos fijados: dos muestras RSS antes/después de una inferencia sintética. Detalle y límites en `modelos-hardware.md`; no mide pico ni equivale a GPU separada. Procesos cerrados por PID y puertos libres.
- **01-nov 02:26 · Playwright y axe.** Tres pasadas con 180 aprobadas y 4 live omitidas cada una, en el puerto 3180. Se usó Node 26 del sistema para Playwright; el check de proyecto utilizó las versiones fijadas por mise.
- **01-nov 02:25 · Auditoría preliminar.** Clon limpio del commit `e634a11`: TOTAL 0. No sustituye la auditoría del tag, que aún no existe.
- **01-nov 02:24 · Bloqueo del recorrido ZIP.** Los archivos de llama.cpp b12020 que incluye el empaquetador no están disponibles; descargarlos e instalarlos excede la autorización limitada a lockfiles. La decisión y alternativa quedan en `decisiones-pendientes.md`.
- **01-nov 02:23 · Check de continuación.** `mise run check` correcto: 313 tests del servicio, 35 live omitidos, 26 de scripts, lint, tipos, contrato y build. Entornos instalados desde los lockfiles dentro del worktree nocturno.
- **01-nov 02:22 · Comparación exploratoria de troceado.** Dos PDF sintéticos y seis hechos literales: secciones 6/6 íntegros, ventanas fijas de 64 caracteres 2/6. `evidence/chunking/` contiene el método y el comando; no mide recuperación ni acredita resultados generales. A2 pasa de no a parcial.
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

## 19:30 · Citas inline, visor a pantalla completa y subida con progreso (v0.12.0)
- Qué cambió: Markdown válido en respuestas panorámicas y citas acotadas a lo que sostiene la respuesta; marcadores inline con vista previa; visor modal con resaltado del fragmento; modal «Añadir fuentes» y aviso persistente con las etapas reales de ingesta por SSE (ADR-011).
- Qué se probó: `mise run check` → OK (146 tests del servicio, 14 de scripts); Playwright 118 de 118, tres pasadas seguidas, con axe en rutas, temas y modos (también visor, diálogo de subida y aviso); gold-v2 en borrador, antes y después: respondidas 23/33 → 24/33, rechazadas correctas 11/11 → 11/11, sin respaldo 0 → 0, marcador inline en 24/24 respuestas con cita; modo `model`: 26/33, 8/11 y 3 sin respaldo, por eso no es el valor por defecto. Resaltado verificado sobre un PDF real; subida real con OCR, duplicado y archivo no admitido.
- Decisión clave y por qué: el valor por defecto de las citas inline es la asignación por reglas, no el LLM de 4B, porque el modo `model` dejó pasar respuestas sin respaldo; el resaltado se calcula al vuelo, sin migrar el índice.
- Pendiente: resaltar una región en facturas (exige guardar las cajas del OCR), teclado virtual real en móvil, medir la latencia de `rules` sin otras cargas, repetir la medida con el gold aprobado.

## 21:00 · Facturas con plan validado y resolución en código (v0.13.0)
- Qué cambió: ver ADR-012. El LLM solo propone la intención y las pistas. Personas, números, roles, años y campos se resuelven en código sobre tablas derivadas tipadas. La ambigüedad se resuelve preguntando.
- Qué se probó:
  - 155 tests (ruff y mypy limpios).
  - Baterías con LLM real en puertos aislados: A 36/36 y B 33/33, sin respuestas falsas; v0.11 sobre las mismas: 6/36 y 7/33, con 11 falsas en total.
  - Índice de 2.005 facturas: 10 correctas y 5 aclaraciones legítimas, con p50 1,6 s en la vía de facturas y 33 ms en la parte determinista.
  - Migración sobre una copia del índice: 35 ms la primera vez, 5 ms después, sin tocar `facturas`.
- Decisión clave y por qué: el año, el rol y los campos salen de la pregunta, porque el modelo de 4B inventaba años y omitía campos. Preguntar es mejor que elegir una factura al azar.
- Pendiente: un gold aprobado, pistas en otros idiomas y triggers de cambios para índices muy grandes.


## Integración de v0.13.0 sobre v0.12.0
- Qué cambió: ADR-011 se mantiene para citas inline y ADR-012 identifica las consultas de facturas. El resultado v2 entrega elementos con sus citas a `AnswerBuilder`; conserva valores, selectores, datos ausentes, límites de lista, notas de revisión y aclaraciones. La subida conserva su progreso real.
- Qué se probó: `mise run check` OK con 218 tests del servicio y 14 de scripts, contrato sin deriva, lint, tipos y build. Playwright 118/118 en tres pasadas seguidas, con axe sin violaciones serias ni críticas. Los cuatro tests que requieren el stack de fixtures se omiten en estas pasadas. Revisión independiente favorable y regresiones sintéticas de las cuatro intenciones, Markdown, citas, truncado y campos ausentes.
- Migración: aditiva e idempotente al primer acceso que abre `InvoiceDB`, no en el lifespan de FastAPI. No requiere reindexar PDFs ni repetir OCR o embeddings de facturas existentes.

## 22:40 · Aclaración de facturas y vista previa de citas (v0.13.1)
- Qué cambió: la ambigüedad en facturas deja de ser un rechazo. El servicio emite `clarification` con hasta 5 candidatas (número, emisor, cliente, fecha, total si existen y la pregunta desambiguada) y la web las pinta como botones accesibles que reenvían esa pregunta (ADR-013). La vista previa de la cita inline queda anclada al marcador, con margen en los bordes y oculta si el marcador sale del hilo.
- Qué se probó: `mise run check` OK (225 tests del servicio, 14 de scripts, contrato sin deriva, eslint, tsc, build). Playwright 139 de 139 en tres pasadas seguidas, con axe sobre la aclaración en cuatro temas y modos. Los tests de la vista previa se vieron fallar antes del arreglo (centrado a 3,83 px, panel flotando con el hilo desplazado). Capturas antes (v0.13.0) y después con el kit real en 1440x900 (industrial claro, neutral oscuro) y 390x844, revisadas una a una; solo en local. Capturas sintéticas en `evidence/screenshots` y `evidence/evolution/v0.13.1`.
- Decisión clave y por qué: la aclaración tiene tipo propio en el contrato porque `suggestions` no puede llevar datos de factura ni la pregunta a reenviar; el servicio construye esa pregunta con una tabla cerrada de frases por campo, para que la web no tenga que inventar texto.
- Pendiente: candidatas de persona para preguntas de lista, conteo o suma (hoy la pregunta de seguimiento es «¿Qué datos tiene la factura X?»); la vista previa puede tapar el compositor en pantallas bajas; teclado virtual real en móvil.

## 23:34 · La vista previa de la cita ya no tapa el composer (v0.13.2)
- Qué cambió: la tarjeta de la cita usa el elemento de scroll del hilo como límite de colisión (`collisionBoundary` de Base UI) y limita su altura a `--available-height`. Con una cita al final del hilo se abre hacia arriba, centrada en el marcador, y termina antes del composer; sigue ocultándose si el marcador sale del hilo. Un solo punto de entrada (`InlineCitationCardBody`) sirve a los marcadores inline y a las pastillas.
- Causa raíz: `collisionBoundary` toma por defecto los ancestros de recorte del popup, y al ir en un Portal solo quedaba la ventana (leído en `useAnchorPositioning` de Base UI 1.9.0). El composer está fuera del hilo pero dentro de la ventana.
- Qué se probó: `mise run check` OK (225 tests del servicio, 14 de scripts, contrato sin deriva, eslint, tsc, build). Playwright 142 de 142 en tres pasadas seguidas, con axe. Una pasada intermedia falló un test de la vista previa (la tarjeta no llegó a abrirse: el ratón se posó en un marcador con el hilo aún desplazándose); el test espera ahora a que el hilo se quede quieto, 84 de 84 con 12 repeticiones y tres pasadas limpias después. Los 3 tests nuevos (marcador inline y pastilla al final del hilo; hilo más bajo que la tarjeta) fallan sin el arreglo, con 45, 85 y 45 px de solape, y pasan con él. Medido con el kit real: 40 px de solape antes y 0 después en 1440x900 y 12 px y 0 en 390x844. Capturas sintéticas antes y después: 46 o 47 px y 0 px en los 12 tamaños y temas.
- Decisión clave y por qué: el límite lo da el hilo y no una lista de «cosas que no tapar», así que cualquier elemento fijo bajo el hilo queda protegido sin conocerlo. La altura máxima evita el solape cuando ni arriba ni abajo cabe la tarjeta entera.
- Pendiente: teclado virtual real en móvil. La tarjeta de rechazo enseña «motivo: …» con el código interno.

## 01:10 · Importes es-ES, solo lo pedido y rechazo sin códigos (v0.13.3)
- Qué cambió: `invoice_fields.py` concentra, para cada campo de factura, su etiqueta, su tipo (texto, fecha, importe, porcentaje) y los términos con que se pregunta. El servicio formatea los importes en es-ES («1.706,60 €») y solo muestra los campos que la pregunta pide, con su propio término cuando es único. La tarjeta de rechazo titula el caso con lenguaje llano y deja el código interno (`llm_unanswerable`, `invoice:*`) en Sistema. Los puertos de modelos salen de un registro único (`_common.py`) y de variables de entorno, con detección de puerto ocupado.
- Qué se probó: `mise run check` OK (298 tests del servicio, 26 de scripts, contrato sin deriva, eslint, tsc, build). Batería sintética de 35 preguntas con invariantes (ningún decimal crudo ni «EUR», importes solo de las facturas elegidas, cita visible en el texto, solo campos pedidos) y 0 respuestas falsas; la misma con el modelo real: 35/35. Playwright 148 de 148 en tres pasadas seguidas, con axe. Capturas sintéticas `chat-rechazo-*` y `chat-factura-*` en `evidence/screenshots`.
- Decisión clave y por qué: el formato del importe no se pide al modelo ni se corrige en la web; sale del valor guardado en el servicio, para que el texto, la cita y la web digan lo mismo. Se prefiere quitar un campo no pedido a adivinar si estorba.
- Pendiente: las fechas se muestran como están guardadas; el espacio del importe puede partirse en móvil (los chips de v0.14.0 lo resuelven); `.github/workflows/cross-platform.yml` conserva los puertos por defecto.


## 01-Nov 01:33 CET · Diseño de respuestas enriquecidas
- Comparadas A cliente/Markdown, B bloques del servicio y C híbrido. Elegida B en ADR-014 por evidencia por dato y degradación al Markdown; contrato con versión explícita. Documentado qué había en el WIP y qué falta verificar/corregir.

## 01-Nov 01:35 CET · Servicio y contrato de bloques
- Fichas/listas/comparativas derivadas de SQL, número de fila citado y sumas con operación y citas de operandos. Versionado explícito `blocks_version: 1`; OpenAPI y cliente regenerados. Corregida pregunta por número que devolvía total y formato de importes en inventario. Markdown conserva los datos generales, incluido número.
- Verificación: suite del servicio 307 passed / 35 live omitidos antes de añadir dos regresiones; batería y streaming repetidos con las nuevas invariantes.

## 01-Nov 01:36 CET · Bloques y microinteracciones de lectura
- Ficha y tabla con citas junto a cada valor; validación de estructura y correspondencia de documento/campo/valor, conjunto atómico y versión desconocida con alternativa Markdown. Copia TSV alineada y con notas, atajos fuera del editor, skeleton y streaming breve. Movimiento reducido también desactiva el scroll programático suave. Revisión independiente de servicio y UI aplicada. Primera pasada de bloques: 30/30 con axe; ampliada después para cubrir el pegado y Option.

## 01-Nov 01:37 CET · Verificación inicial y comparación de números
- `mise run check` completo correcto con 309 tests del servicio y 26 de scripts, eslint, tipos, build y contrato sin deriva. La revisión independiente adicional detectó columna número duplicada en comparativas de números; eliminada en la vista tabular y añadida regresión sintética. No altera valores ni extracción.

## 01-Nov 01:39 CET · Corrección de expectativa del lector SSE
- La primera suite completa dio 179 pasadas, 1 fallo y 4 omitidas. El fallo era una expectativa del test de tramas crudas: se había añadido blocks_version al sobre SSE en vez de a su JSON. Corregida solo la expectativa; la trama cruda no lleva ese campo. Se repetirán tres pasadas completas tras esta corrección.

## 01-Nov 01:40 CET · Batería sintética y captura de línea base
- Batería con modelo real aislado en 8171: 81 tests pasados, incluidos 35 casos live con invariantes de ausencia de respuestas falsas. Las pruebas adicionales de bloques comprueban igualdad de valor/cita y operandos de sumas.
- Capturado el antes con una exportación del tag v0.13.3 y sus propios servicio/web; mismo índice local de humo y modelos propios, sin usar puertos de Miguel. Capturas reales solo fuera del repo.
- La segunda pasada ya en curso había cargado la expectativa SSE antigua y repitió ese fallo. Se reinicia ahora una secuencia nueva de tres pasadas contra la expectativa corregida.

## 01-Nov 01:43 CET · Ficha general estable y oráculo de batería
- La presentación de datos generales se limita determinísticamente a emisor, cliente, número, fecha y total incluso si el plan propone todos los campos. Reproducido con fixture sintética y plan sobrecargado; sin cambiar parser de extracción ni prompts. La batería comprueba ahora todas las celdas y valores esperados también con modelo real. La formulación ambigua total de las facturas admite suma o desglose, conservando los dos importes esperados. Primera pasada final e2e: 180/180, 4 live omitidas.

## 01-Nov 01:48 CET · Tests finales y revisión independiente cerrados
- Corregidos los dos casos de borde de la última revisión: datos bancarios conserva solo IBAN; la prueba de falsa suma rechaza un total alterado aunque los operandos sean correctos. Revisión independiente reabierta y favorable tras ambas correcciones.
- `mise run check` final OK: 313 tests del servicio, 35 live omitidos en esa ejecución, 26 tests de scripts; ruff, mypy, eslint, tipos, contrato sin deriva y build. Batería separada con modelo real: 84/84, incluidos 35 live, 0 respuestas falsas bajo sus oráculos y aritmética Decimal. Playwright: 180/180 ×3, 4 pruebas de fixtures live omitidas por pasada; axe sin violaciones serias ni críticas en las rutas y variantes probadas.

## 01-Nov 01:45 CET · Capturas sintéticas y reales inspeccionadas
- Comparación sintética desde v0.13.3: 36 parejas en evidence/comparison-v0.13.3-v0.14.0/ y 2 capturas móviles desplazadas; galería y screenshots con 38 imágenes nuevas/actualizadas. Inspección de todas las variantes mediante hojas de contacto, más vistas a tamaño original. El scroll queda dentro de la tabla: página 390 px, contenedor 326 px y contenido 453–455 px; importes visibles al desplazar. Ficha de cinco datos y precio final revisados en escritorio y móvil.
- Reales: 12 antes + 12 después en _agents/ui7/shots/v0.14.0/, solo fuera del repo. Antes con tag v0.13.3 exportado; después con servicio actual. Repetidas las cuatro capturas de datos clave tras fijar la presentación de cinco campos y miradas las finales. Sin modificaciones a extracción ni prompts. Puertos propios 3170/8170/8171–8174, modelos en carpeta externa.

## 01-Nov 01:49 CET · Documentación de v0.14.0 actualizada
- CHANGELOG, contrato SSE, sistema de diseño, ADR-014, diseño y revisión reflejan el resultado final. Cobertura con resumen de tres líneas: mejoran B3/B4/B5 y E-A3/E-A4; pendientes gold y posiciones OCR; 17 cumplidas, 10 parciales, 4 no. Pruebas y capturas enlazadas con sus límites. Se prepara auditoría en clon limpio antes del tag y otra sobre el tag final.

## 01-Nov 01:51 CET · Cierre documental y auditoría preliminar
- Auditoría en clon limpio del commit f4cd57c: TOTAL 0 en _agents/ui7/audit-pre-v0.14.0.txt; clon movido a _trash/audit-clone-pre-v0.14.0. Humo final del servicio con fuentes locales: ficha general de cinco campos, precio final específico y tabla de cinco filas, con valores contrastados contra las filas almacenadas y todas las citas correctas; solo salida privada en _agents/ui7/release-smoke.json. El informe del tag final se guarda en _agents/ui7/audit-v0.14.0.txt. No se cambia la acreditación pendiente del gold.

## 01-Nov 01:53 CET · Auditoría del tag y parada por PID
- Tag anotado v0.14.0 auditado en clon limpio sobre bb87d39: TOTAL 0 en _agents/ui7/audit-v0.14.0.txt; clon en _trash/audit-clone-v0.14.0. Este cierre documental se incorpora al último commit y la auditoría se repite sobre el tag definitivo. Parados por SIGTERM únicamente los PID propios 65810, 50708, 2292, 2312, 2322 y 2333; puertos 3170/8170/8171–8174 libres. Exportación de la versión anterior movida a _trash/. Main conserva d4eca6c y v0.13.3 conserva b962ccc. Sin push ni instalaciones en esta continuación.

## 01-Nov 01:56 CET · Inventario del hardware
- `sysctl`, `sw_vers` y `system_profiler` identifican Apple M4, CPU y GPU de 10 núcleos, 16 GiB de memoria unificada y macOS 26.6.2. README registra los comandos y distingue capacidad de consumo medido. C3 pasa a cumplido; E-B2 sigue parcial.
- Verificación: salida de los tres comandos contrastada con README y cobertura. Sin instalaciones. La fase sigue abierta y aún no tiene tag.


## 01-Nov 01:56 CET · Decisiones pendientes
- Registradas las decisiones sobre gold y umbrales, privacidad del historial e identidad. Las recomendaciones no implican aprobación ni cambian el estado del gold.
- Verificación: recuento automático de las 31 filas: 18 cumplidas, 9 parciales y 4 no. La fase continúa abierta.


## 01-Nov 01:57 CET · Inventario de modelos
- Documentados los cinco archivos, cuantizaciones y tamaños fijados. Los 5,072 GiB son tamaño en disco, no memoria usada. C4/C5/E-C1 y E-B2 siguen abiertos a falta de medidas y comparación.
- Verificación: tamaños calculados desde `scripts/assets.json`; cuatro tests de troceado pasaron con el entorno Python ya existente de ui7, sin instalar dependencias.


## 01-Nov 01:57 CET · Límite de fundamentación en el README
- Sustituida la promesa de ausencia de invenciones por una descripción de las verificaciones y su límite heurístico, coherente con `docs/architecture.md`. No se afirma una tasa de error sin gold aprobado.
- Verificación: revisión del texto y `git diff --check`. Sin cambios de comportamiento.


## 01-Nov 01:57 CET · Línea base de pruebas Python
- Ejecutados los tests del worktree con el intérprete ya existente de ui7 y `PYTHONPATH=services/ai/src`: 313 pasados y 35 omitidos en servicio; 26 pasados en scripts. Un aviso de deprecación de Starlette. No equivale a `mise run check` ni a las pruebas live.
- No se instaló nada ni se arrancaron servidores. Pendiente autorización para instalar dependencias locales y completar los checks exigidos.


## 01-Nov 01:58 CET · Propuesta multiusuario
- Añadida arquitectura para cientos de usuarios registrados: SSO, inquilinos y ACL por documento, recuperación autorizada, colas, almacenamiento, caché, observabilidad, despliegue y costes. La capacidad simultánea queda pendiente de medición.
- Corregidas afirmaciones no medidas sobre GPU y coste, la cabecera de identidad como confianza suficiente y la colisión con ADR-014. Revisión documental y `git diff --check`; fase aún sin cierre ni tag.


## 01-Nov 02:00 CET · Revisión privada del gold
- Copia byte a byte del borrador de 44 casos y revisión de cada caso frente a los cuatro PDF. Detectados M03 (confusión de dos tareas), Z01 (citas incompletas y señales frente a alimentación) y otras ambigüedades. Informe y datos solo en `_agents/night/`. No contiene casos de facturas.
- Preparado colector de una pasada para un gold aprobado, probado con dos casos sintéticos y transporte simulado; no califica ni se ejecutó con datos reales. El primer intento de prueba con servidor temporal quedó bloqueado y se terminó solo su PID 95809. El servicio ajeno que escucha en 8000 no se tocó. Sin evaluación final ni tag.


## 01-Nov 02:00 CET · Puertos de la matriz multiplataforma
- El workflow manual configura 3180, 8180 y 8181–8184 y comprueba esos puertos al cerrar. Sigue sin ejecutarse en GitHub; el OCR falso no arranca un proceso.
- Verificación estática: YAML leído, variables comprobadas y bloque Python compilado con el entorno existente. Sin instalaciones ni servicios iniciados para esta comprobación.


## 01-Nov 02:00 CET · Estado sin publicar
- CHANGELOG y cobertura distinguen el trabajo sin publicar de v0.14.0 e incluyen el resumen de tres líneas. Corregido el recuento de procesos descrito en escalado.
- `git diff --check` correcto. No se declara cierre de fase ni tag sin los checks solicitados.


## 01-Nov 02:02 CET · Auditoría preliminar
- Clon limpio de `feat/core-v0.15` en 7801718: `audit-preliminar.txt` informa TOTAL 0. El clon propio se movió a `_trash/audit-night-preliminar-*`.
- Es una auditoría previa, no sustituye la auditoría del tag definitivo. No hay tag nuevo.


## 01-Nov 02:02 CET · Revisión estática de portabilidad
- Documentados plataformas empaquetadas, rutas, procesos y límites de la matriz. Detectada incompatibilidad entre la regla de esta sesión de usar solo PID y el cierre por grupo de `dev.py` y `package.py`; no se ejecutaron esos scripts. El ZIP no incluye binarios para todas las arquitecturas de `assets.json`.
- Revisión estática y `git diff --check`; no sustituye pruebas en macOS, Windows o Linux.


## 01-Nov 02:02 CET · Estado de continuación
- No hay tags nuevos. Rama `feat/core-v0.15`; no se ha hecho push ni merge. Auditoría preliminar TOTAL 0 sobre el commit indicado arriba, no sobre este cierre.
- Mejoran C3, el inventario de C4/C5/E-C1 y la propuesta de S1–S3. Pendientes gold aprobado, comparación de troceado y modelos, memoria de ejecución y pruebas de portabilidad. Recuento 18 cumplidas, 9 parciales y 4 no.
- Pendiente autorización expresa para instalar dependencias locales. También debe resolverse el cierre por grupos de los scripts antes de ejecutar el recorrido en esta sesión, que exige solo PID. No se han ejecutado check completo, tres pasadas e2e con axe, capturas nuevas, ni auditoría de tag. Historial y feedback no se han iniciado.
- Gold y revisión privados: `gold-v2-borrador.jsonl`, `gold-v2-revision.md` y `recoger-evaluacion.py`. La recogida solo se probó con transporte simulado; no es una evaluación puntuada ni se ejecutó con fuentes reales.

## 01-Nov 03:03 CET · Errores de modelo
- Los errores HTTP 429 y 503 y los tiempos de espera tienen códigos y mensajes para reintentar. El planificador de facturas propaga estos errores en lugar de tratarlos como planes inválidos. El contrato conserva los campos existentes.
- Pasaron 102 pruebas focalizadas y Ruff. Pendientes cola, carga ampliada, check completo y auditoría de la versión.

## 01-Nov 03:07 CET · Acceso concurrente a PDFium
- Una carga de consultas e ingestas terminó el proceso dentro de PDFium. El servicio ahora serializa la creación, uso y cierre de objetos PDFium entre ingesta, validación y localización de citas.
- Una prueba fuerza el solapamiento entre ingesta y localización y comprueba la exclusión. En la repetición con modelos locales, 12 consultas dieron respuestas verificadas con citas y 4 PDF se indexaron. La muestra no demuestra ausencia de otras carreras.

## 01-Nov 03:09 CET · Código de error en Sistema
- La última traza conserva el código de un fallo incluso si ocurre antes del primer paso. Sin pasos, el botón de reproducción queda desactivado.
- Pasaron 13 pruebas del transporte. `mise run check` pasó con dependencias ya existentes y una raíz temporal ampliada para Turbopack; la primera ejecución con la configuración original falló en build por los enlaces externos. Pendientes pruebas visuales de este cambio y check en un entorno de dependencias local al worktree.

## 01-Nov 03:12 CET · Prueba visual del error
- La prueba de navegador confirma el mensaje en chat y el código en Sistema para un fallo antes de cualquier paso. Las capturas sintéticas antes y después están en `evidence/comparison-v0.15.1/` y se inspeccionaron. La primera ejecución focalizada usó un directorio de trabajo incorrecto y no llegó a ejecutar la prueba; repetida desde `apps/web` pasó.

## 01-Nov 03:13 CET · Documentación de trabajo sin publicar
- CHANGELOG y cobertura registran los cambios de robustez y sus límites. El recuento de requisitos no cambia; la serie de navegador y la fase siguen abiertas.

## 01-Nov 03:14 CET · Entorno de verificación
- Registrada la autorización pendiente para instalar las dependencias de los lockfiles en este worktree. El check con enlaces y raíz temporal ampliada pasó; el build con la configuración original no resolvió dependencias externas.

## 01-Nov 03:15 CET · Tres pasadas de navegador
- Tres pasadas del build corregido: 182 pruebas aprobadas y 4 live omitidas en cada una, con axe en las rutas cubiertas. El build se generó con la raíz temporal ampliada y dependencias existentes. Las capturas sintéticas del fallo se inspeccionaron.
- El servidor propio se cerró por PID. Se retiraron a `_trash/` los enlaces y la configuración temporal. Continúan pendientes la cola y el cierre de versión.

## 01-Nov 03:16 CET · Cola acotada de consultas
- Cada proceso admite dos consultas activas y cuatro en espera durante un máximo de 60 segundos. El flujo indica la espera con un paso existente; al llenarse o agotarse devuelve un error recuperable. `/ask` devuelve HTTP 503 para ambos casos.
- Cuatro pruebas deterministas cubren espera, capacidad, desconexión, timeout y el endpoint sin streaming. Pasaron 36 pruebas focalizadas y mypy. La cola es local al proceso y no limita ingestas; falta repetir carga con modelos y las verificaciones de entrega.

## 01-Nov 03:16 CET · Corrección sobre el check anterior
- El entorno Python reutilizado tiene una instalación editable que apunta al worktree anterior. El `mise run check` de las 03:09 probó ese código del servicio, no el de este worktree. Las pruebas focalizadas sí utilizaron `PYTHONPATH` explícito. Se regenera el contrato y se repetirá el check con la ruta del código actual.

## 01-Nov 03:17 CET · Carga con cola
- Con modelos locales, 12 consultas y 4 PDF en hasta 8 tareas: 6 consultas devolvieron respuesta verificada, 6 recibieron `queue_full` y los 4 PDF se indexaron. Cuatro consultas mostraron el paso de espera. El HTTP 200 de SSE no representa por sí solo el resultado del flujo.
- Los procesos de la prueba se cerraron por PID. La prueba no mide equidad ni comportamiento sostenido y no reproduce la carga de facturas.

## 01-Nov 03:18 CET · Check con código actual
- `mise run check` pasó con `PYTHONPATH` apuntando al servicio actual: 322 pruebas del servicio y 26 de scripts, 35 live omitidas, Ruff, mypy, ESLint, tipos, contrato sin deriva y build. El build usó la raíz temporal ampliada para resolver dependencias existentes; después se retiró la adaptación.
- Se repiten las pasadas de navegador con el build final. La autorización de dependencias locales sigue en decisiones pendientes.

## 01-Nov 03:21 CET · Cierre de verificaciones v0.15.1
- Tres pasadas del build final dieron 182 aprobadas y 4 live omitidas por pasada, con axe en las vistas cubiertas. Cerrado por PID el servidor propio; puertos propios libres. Los enlaces de dependencias y la configuración temporal se movieron a `_trash/`.
- Mejoran la concurrencia PDF, la admisión de consultas y los mensajes de error. Pendientes la evaluación sintética, los percentiles, la equidad de la cola y el check en un entorno local de dependencias. Recuento: 18 cumplidas, 10 parciales y 3 no.

## 01-Nov 03:22 CET · Auditoría v0.15.1
- La auditoría del tag `b48094a` en un clon limpio terminó con TOTAL 0. Sus temporales se aislaron para no sobrescribir los archivos `/tmp/aud-*` existentes; el clon y esos temporales se movieron a `_trash/`.

## 01-Nov 03:25 CET · Evaluación sintética
- Copiado el borrador privado sin aprobar y añadidos 11 casos sintéticos a una copia ampliada. El caso de aclaración queda aparte porque el esquema binario no representa esa salida.
- Una ejecución con modelos locales sobre dos PDF y tres imágenes sintéticas obtuvo 7 coincidencias de 12 con un oráculo limitado. Las tres facturas quedaron en revisión por importes incompletos y cinco preguntas no cumplieron la expectativa. El informe de `evidence/evaluacion-sintetica/` conserva los límites y resultados; no se evaluaron facturas reales.

## 01-Nov 03:27 CET · Etiquetas de importes con dos puntos
- El OCR de una imagen sintética conservó las etiquetas y cantidades; el extractor no aceptaba dos puntos tras las etiquetas de base, IVA y total. La corrección reconoce ese separador y conserva la evidencia literal.
- Una regresión fallaba con el patrón anterior; tras el cambio pasaron 120 pruebas focalizadas y se omitieron 35 live. Falta repetir la batería sintética completa y los checks de entrega.

## 01-Nov 03:28 CET · Repetición sintética
- Tras corregir el separador, las tres facturas sintéticas quedaron con estado `ok` y sus totales esperados. El mismo oráculo pasó de 7 a 11 coincidencias de 12. En el caso restante se esperaba aclaración y el sistema listó ambas facturas con sus importes y citas; no se presenta como una cifra falsa.
- Se cerraron por PID los procesos propios. Los resultados completos y las fuentes sintéticas permanecen fuera del repositorio; el borrador sigue sin aprobar.

## 01-Nov 03:30 CET · Verificaciones v0.15.2
- `mise run check` pasó tras la corrección con 323 pruebas del servicio, 35 live omitidas y 26 de scripts, lint, tipos, contrato y build. Se usaron dependencias existentes y raíz temporal ampliada para Turbopack; la adaptación se retiró.
- Tres pasadas de navegador con axe dieron 182 aprobadas y cuatro live omitidas cada una. Usaron respuestas simuladas; se ejecutaron antes del cambio del extractor, que no modifica la interfaz. El servidor propio se cerró por PID y los temporales se movieron a `_trash/`.
- Mejoran extracción de importes con dos puntos y evaluación sintética. Pendientes gold aprobado, evaluación representativa y percentiles. Recuento: 18 cumplidas, 10 parciales y 3 no.


## 01-Nov · Cierre documental v0.15.3

- Añadidos el índice documental, las rutas de lectura y las notas de v0.14.0 a v0.15.2. Arquitectura, estructura, huecos, pendientes y versionado contrastados con el árbol v0.15.2 y su historial.
- El comprobador local revisó README y los Markdown de docs: 28 documentos y 135 enlaces internos, sin enlaces rotos. Se repararon rutas de la revisión histórica y se conservaron sus referencias a líneas originales.
- Este cierre solo cambia documentación. No repite pruebas de código ni instala dependencias; los límites de evaluación y entorno de v0.15.2 siguen vigentes.

## 01-Nov 13:16 CET · Conexión inicial del historial

- Conectados el stream, la cola de reintentos y las rutas locales de historial y revisión. El arranque comparte un token efímero entre la API y el proxy; la retención se ejecuta al arrancar y cada hora. El historial se puede desactivar mediante configuración del administrador.
- Las pruebas de integración cubren purga, autorización y fallos de almacenamiento sin alterar el evento final. Pasaron 381 pruebas del servicio y se omitieron 35 live; después pasó la prueba adicional de fallo de escritura. El contrato generado conserva las propiedades anteriores. La cola pendiente está en memoria y se pierde al reiniciar.
- Quedan pendientes la interfaz, las capturas y las verificaciones de entrega. La base actual es local y no proporciona aislamiento multiusuario.

## 01-Nov 14:05 CET · Historial local y feedback

- El panel permite buscar, abrir y borrar conversaciones; Sistema muestra la cola de guardado y la revisión humana. El feedback solo incluye contexto si se solicita. La cola de escrituras es volátil ante reinicios.
- El check completo reutilizó las dependencias existentes: 392 pruebas del servicio y 26 de scripts pasaron, con 35 live omitidas; lint, tipos, contrato y build correctos. El build utilizó temporalmente una raíz de Turbopack ampliada.
- El humo con modelos locales usó fuentes sintéticas y produjo una respuesta documental y otra de factura con citas, una aclaración y un rechazo. Las cuatro consultas quedaron guardadas. Una repetición completa en una sola ejecución verificó las cuatro consultas guardadas y un aviso revisado y exportado. La prueba no acredita precisión general.

## 01-Nov 14:15 CET · Recuperación y revisión de interfaz

- Si SQLite no abre al arrancar, la cola conserva las consultas y reintenta; Sistema distingue ese fallo de una desactivación. Una prueba integrada verifica la recuperación, el `request_id` y el stream intacto. La cola sigue siendo volátil ante reinicios.
- Paginación probada con 101 conversaciones y 101 avisos. Un fixture derivado del humo sintético restaura dos respuestas con citas, una aclaración y un rechazo. Los formularios usan componentes shadcn sobre Base UI y las vistas focalizadas pasan axe.

## 01-Nov 14:23 CET · Verificación de historial y feedback

- `mise run check` terminó correctamente con 395 pruebas del servicio, 35 live omitidas y 26 pruebas de scripts; lint, tipos, contrato generado y build correctos. El build reutilizó dependencias existentes y una raíz de Turbopack ampliada temporalmente.
- Tres pasadas Playwright con axe dieron 199 aprobadas y cuatro live omitidas cada una. Cubren las vistas de historial y revisión, la paginación de 101 elementos, restauración de resultados sintéticos reales y contraste del botón en hover en cuatro temas y modos.
- El humo con modelos locales comprobó en una sola ejecución una respuesta documental y otra de factura con citas, aclaración y rechazo, las cuatro consultas guardadas y un aviso revisado y exportado. Son datos sintéticos, no una medida de precisión general.

## 01-Nov 15:07 CET · Consulta de peticiones recientes

- La API ofrece una consulta paginada y local de metadatos de peticiones; no incluye pregunta, respuesta ni citas. El contrato se amplía sin eliminar rutas. Las pruebas cubren orden, paginación, límites y autorización.
- Pendiente conectar la vista de Sistema y completar la revisión y las verificaciones de v0.17.1.

## 01-Nov 15:09 CET · Sistema e historial contextual

- La API real devolvió una conversación sintética que Sistema no mostraba: la vista solo consultaba estado y avisos. Se añade una tabla paginada de peticiones, con identificador copiable y metadatos de estado; los fallos de escritura sin persistir siguen en el estado del historial.
- Se compararon dos paneles laterales. Historial abre ahora en un panel derecho estrecho que puede ampliarse; conserva búsqueda, borrado y Alt+H. Pasaron pruebas focalizadas de navegador y comprobaciones de tipos y lint; queda pendiente la batería completa.
