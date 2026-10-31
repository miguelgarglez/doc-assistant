# Estructura del repo
```
mise.toml            herramientas fijadas + tareas (1 comando cada una)
package.json         raíz del pnpm workspace (packageManager fijado)
pnpm-workspace.yaml  apps/*
config/config.yaml   config del servicio IA (validada con Pydantic al arrancar)
scripts/
  _common.py         rutas/plataforma compartidas
  assets.json        llama.cpp b12020 + modelos, con SHA256
  setup.py           uv sync, pnpm install, build, llama-server, modelos
  dev.py             arranque único: llama x3 → IA → web; Ctrl-C limpio
  check.py           ruff, mypy, pytest, contrato sin drift, eslint, tsc, build
  fake_llama.py      simula llama-server (CI)
services/ai/         doc_assistant (FastAPI): api, ask, verifier, ingest, chunking,
                     store (SQLite+sqlite-vec), invoices, adapters (puertos), config
                     openapi.json = contrato (fuente de verdad)
apps/web/            Next.js 16 + TS strict
  src/app/api/[...path]/route.ts   proxy fino → servicio IA (BFF)
  src/lib/api/schema.d.ts          tipos generados desde openapi.json
  src/components/ui/               primitivos shadcn sobre Base UI
  src/components/domain/           AnswerCard, CitationChip, SourceViewer, RefusalNotice,
                                   InvoiceReviewCard, UploadDropzone
.github/workflows/cross-platform.yml   smoke Win/Linux/Mac (no ejecutado)
docs/                ADRs, CHECKPOINT, estructura; architecture y scaling (pendientes)
evidence/            evidencia regenerable (pendiente)
vendor/, models/     binarios y GGUF (git-ignorados)
_trash/              en vez de borrar (git-ignorado)
```
