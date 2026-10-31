# CHANGELOG

Fechas del commit etiquetado (Europe/Madrid). Detalle de pruebas en cada tag (`git tag -n99 vX`) y en `CHECKPOINT.md`. Capturas por versión: `evidence/evolution/README.md`.

## v0.4.0 · 2026-10-31 13:12 · a1855f2
- Auditoría de tests del slice (26 migrados, 55 excluidos a propósito, 0 perdidos).
- Facturas: OCR → reglas Decimal → LLM para texto; puertas de suma/IVA → "revisar"; consultas SQL con cita.
- POST /documents; /ingest confinado. Web: dominio corregido, visor lado a lado, capturas móvil.
- Probado: check (42+5 tests), e2e 6 passed, 6/6 facturas sintéticas sin discrepancias.

## v0.3.0 · 2026-10-31 12:50 · f6b06c7
- Web conectada al API real con cliente openapi-fetch; citas abren la página con el fragmento.
- Setup resuelve la carpeta de modelos y no redescarga.
- Probado: check OK, e2e 3 passed, setup --verify sin descargas.

## v0.2.0 · 2026-10-31 12:40 · 5798de1
- LLM con --reasoning-budget 0. Primera pregunta real extremo a extremo.
- Probado (humo): "N kg" con cita en 7 s; rechazo de precio en 5 s.

## v0.1.0 · 2026-10-31 12:32 · 4588e84
- Monorepo FastAPI + Next/shadcn, mise + scripts Python, llama.cpp b12020 con SHA256, contrato OpenAPI con check de deriva.
- Probado: check OK (29 tests), start + Ctrl-C sin huérfanos.
