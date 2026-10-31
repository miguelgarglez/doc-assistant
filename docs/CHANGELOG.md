# CHANGELOG

Fechas del commit etiquetado (Europe/Madrid). Detalle de pruebas en cada tag (`git tag -n99 vX`) y en `CHECKPOINT.md`. Capturas por versión: `evidence/evolution/README.md`.

## v0.13.0 · 2026-10-31
- Facturas en lenguaje natural rehechas (ADR-011):
  - Plan validado por esquema (valor, lista, contar, sumar).
  - Personas y números resueltos en código: tildes, mayúsculas, erratas, NIF con guiones, números parciales o sin ceros.
  - Columnas tipadas e indexadas para fechas e importes, y SQL sobre una lista cerrada de campos.
  - Aclaración «¿te refieres a…?» con candidatas. Si se pregunta un valor, se responde un valor.
  - Citas solo de las facturas seleccionadas.
- Migración aditiva e idempotente al abrir la base (`facturas_q`, `partes_fts`). No cambia `SCHEMA_VERSION` ni el contrato.
- Probado:
  - 155 tests del servicio.
  - Baterías con LLM real: 36/36 (antes 6/36, 6 falsas) y 33/33 adversariales (antes 7/33, 5 falsas).
  - Índice sintético de 2.005 facturas: 0 falsas y 33 ms de parte determinista (p50).

## v0.11.0 · 2026-10-31
- Chat reconstruido sobre AI SDK (`useChat` con un `ChatTransport` propio para `/ask/stream`) y AI Elements adaptados a Base UI: Prompt Input con adjuntos (pegar o arrastrar PDF o imagen), mensajes con Markdown (Streamdown), traza de pasos plegable, píldoras de cita y fuentes plegables que abren el fragmento, Shimmer, sugerencias, copiar y regenerar. Decisión por componente en ADR-010.
- Layout de aplicación a 100dvh: navegación fija, el hilo es el único scroll, composer anclado; visor de citas lateral (hoja inferior en móvil).
- Sistema: diagrama de piezas (navegador, proxy, servicio, LLM, embeddings, reranker, índice, OCR) con estado y latencia reales, y traza de la última consulta que ilumina cada pieza. Nuevo `GET /health/components` en el servicio.
- Fuentes: tabla ordenable (nombre, tipo, páginas, fragmentos, estado, fecha) con filtro de documentos y facturas, detalle lateral y cola de subida con estados y progreso.
- Servicio: plurales correctos en las etiquetas de los pasos ("1 cita verificada").
- Probado: `mise run check`; Playwright 77 pruebas en tres pasadas más 4 contra el stack real (`LIVE_BASE_URL`); axe sin violaciones serias o críticas en las rutas, temas y modos; capturas reales en 1440x900, 1280x720 y 390x844, cuatro combinaciones de tema y modo (`evidence/screenshots`).

## v0.10.0 · 2026-10-31
- Chat acumulado con SSE, pasos de consulta, tokens provisionales y rechazo inmediato que retira el texto no verificado. Comprobado el paso de eventos por el proxy con un servicio de prueba.
- Fuentes reúne documentos y facturas, con páginas, fragmentos y altas. Ajustes concentra tema y modo. Las preguntas panorámicas responden desde el índice (ADR-009).
- Sistema muestra la arquitectura y reproduce la traza; la salud por pieza queda pendiente del endpoint propuesto.
- Adaptación de patrones AI Elements sobre Base UI y decisión detallada en ADR-008.
- Validación: `mise run check` correcto (88 tests del servicio y 14 de scripts), 69 pruebas Playwright en tres pasadas; axe sin violaciones serias o críticas en las cuatro rutas, ambos temas y modos.

## v0.9.0 · 2026-10-31 15:55
- Sistema de diseño intercambiable: temas `industrial` (default) y `neutral`, modo claro/oscuro, página `/design`, guía en `docs/design-system.md` (ADR-007).
- Chat: atajos de teclado, historial de preguntas en sesión, cancelar con AbortController, copiar respuesta/citas/Markdown, pegar/arrastrar PDF e imagen, regenerar, rechazo con diseño propio, auto-scroll que respeta scroll del usuario, progreso de subida.
- Calidad: e2e de comportamiento + axe (0 violaciones serias/críticas en home y `/design`, ambos temas/modos); capturas theme/design desktop y móvil.
- Revisión independiente (13 hallazgos: foco del diálogo, IME, historial ↑, subidas concurrentes, timeout, persistencia, tema antes del pintado, reduced-motion, portapapeles) aplicada.
- Probado: check OK, e2e 38 passed (3 pasadas seguidas), axe 0 serias/críticas en 8 combinaciones.

## v0.8.0 · 2026-10-31 15:00
- OCR de facturas dentro del ZIP: GLM-OCR GGUF en llama-server :8084 por defecto (setup lo descarga con SHA256); Ollama como alternativa documentada. NOTICE con la licencia y la duda.
- Parser de importes: tipos entre paréntesis, base sin tipo y "TOTAL FACTURA".
- Probado: check OK, e2e 12 passed, `mise run package --smoke real` OK (5,53 GB).

## v0.7.0 · 2026-10-31 14:35
- Visor: recorre todas las páginas de un fragmento citado (#23). CI en push/PR con check + e2e (#19).
- Cierre robusto de procesos huérfanos (#14). Setup/start avisan si el OCR de facturas no está listo (#13, parcial).
- Paquete: textos de licencia en `licenses/`; el smoke real sube una factura y comprueba puertos liberados.
- Probado: check OK (11 tests scripts), e2e 12 passed, `mise run package --smoke real` OK.

## v0.6.1 · 2026-10-31 14:05
- Historial reescrito para publicar (nombre público, fixtures neutros, capturas regeneradas por commit); tags recreados en los commits equivalentes. Galería con nota de regeneración.
- Probado: check OK, e2e 11 passed; auditoría de publicación 0 hallazgos.

## v0.6.0 · 2026-10-31 13:41 · 30ed6f5
- Nombre público doc-assistant; cobertura de requisitos, huecos abiertos y escalado a toda la empresa.

## v0.5.0 · 2026-10-31 13:33 · d0ce091
- Revisión aplicada, facturas en la web, empaquetado y evidencia regenerable; esquema SQLite versionado.

## v0.4.0 · 2026-10-31 13:12 · 3ec2f47
- Auditoría de tests del slice (26 migrados, 55 excluidos a propósito, 0 perdidos).
- Facturas: OCR → reglas Decimal → LLM para texto; puertas de suma/IVA → "revisar"; consultas SQL con cita.
- POST /documents; /ingest confinado. Web: dominio corregido, visor lado a lado, capturas móvil.
- Probado: check (42+5 tests), e2e 6 passed, 6/6 facturas sintéticas sin discrepancias.

## v0.3.0 · 2026-10-31 12:50 · 7068e08
- Web conectada al API real con cliente openapi-fetch; citas abren la página con el fragmento.
- Setup resuelve la carpeta de modelos y no redescarga.
- Probado: check OK, e2e 3 passed, setup --verify sin descargas.

## v0.2.0 · 2026-10-31 12:40 · 5f182b4
- LLM con --reasoning-budget 0. Primera pregunta real extremo a extremo.
- Probado (humo): valor correcto con cita en 7 s; rechazo de precio en 5 s.

## v0.1.0 · 2026-10-31 12:32 · e9ca554
- Monorepo FastAPI + Next/shadcn, mise + scripts Python, llama.cpp b12020 con SHA256, contrato OpenAPI con check de deriva.
- Probado: check OK (29 tests), start + Ctrl-C sin huérfanos.
