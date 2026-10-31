# CHANGELOG

Fechas del commit etiquetado (Europe/Madrid). Detalle de pruebas en cada tag (`git tag -n99 vX`) y en `CHECKPOINT.md`. Capturas por versión: `evidence/evolution/README.md`.

## v0.10.0 · 2026-10-31
- Chat acumulado con SSE, pasos de consulta, tokens provisionales y rechazo que retira el texto no verificado.
- Fuentes reúne documentos y facturas, con páginas, fragmentos y altas. Ajustes concentra tema y modo.
- Sistema muestra la arquitectura y reproduce la traza; la salud por pieza queda pendiente del endpoint propuesto.
- Adaptación de patrones AI Elements sobre Base UI y decisión detallada en ADR-008.
- Validación: `mise run check` correcto (87 tests del servicio y 14 de scripts), 69 pruebas Playwright en tres pasadas; axe sin violaciones serias o críticas en las cuatro rutas, ambos temas y modos.

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
