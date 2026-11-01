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
  dev.py             arranque único: LLM, embeddings, reranker, OCR → IA → web; Ctrl-C limpio
  check.py           ruff, mypy, pytest, contrato sin drift, eslint, tsc, build
  fake_llama.py      simula llama-server (CI)
  package.py         ZIP64 de entrega + smoke al descomprimir
  evidence.py        capturas e2e; --live corrida real con fixtures
  evolution.py       galería por tag (evidence/evolution)
NOTICE               licencias de modelos y llama.cpp
services/ai/
  src/doc_assistant/ FastAPI: api, ask, verifier, ingest, chunking,
                     store (SQLite+sqlite-vec), invoices, adapters (puertos), config
                     invoice_blocks (fichas y tablas), ask_capacity (cola por proceso),
                     pdf_lock (acceso serializado a PDFium)
  openapi.json       contrato (fuente de verdad)
apps/web/            Next.js 16 + TS strict
  src/app/api/[...path]/route.ts   proxy fino → servicio IA (BFF)
  src/lib/api/schema.d.ts          tipos generados desde openapi.json
  src/components/ui/               primitivos shadcn sobre Base UI
  src/components/chat/             respuestas, bloques, citas, aclaraciones y visor
  src/components/viewer/           página y resaltado
  src/components/uploads/          diálogo y avisos de subida
  src/components/sources/          gestión de fuentes
  src/components/system/           estado de componentes y última traza
  src/components/ai-elements/      componentes de conversación
  src/components/providers/        estado compartido de chat y subidas
  src/lib/domain/                  tipos y utilidades de dominio
  src/lib/chat/                    transporte SSE, vistas y validación de bloques
.github/workflows/cross-platform.yml   smoke Win/Linux/Mac (no ejecutado)
docs/                README (índice), ADRs, CHECKPOINT, CHANGELOG, versioning, architecture, scaling,
                     requirements-coverage, open-gaps, design/, evolution-notes/, reviews/
evidence/            screenshots/, live/, fixtures/ (sintéticos), evolution/ (por tag),
                     comparison-*/, evaluacion-sintetica/, chunking/, modelos/
vendor/, models/     binarios, archives/ y GGUF (git-ignorados)
_trash/              en vez de borrar (git-ignorado)
```

El [índice documental](README.md) explica qué pregunta responde cada documento. Los diseños de multiusuario e historial son propuestas; su presencia en `docs/design/` no implica implementación.
