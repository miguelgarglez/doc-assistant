# Registro de decisiones (ADR cortos)

## ADR-001 Monorepo con dos servicios (2026-10-31)
- Contexto: el núcleo (LLM, recuperación, OCR, SQLite) exige Python; la UI se evalúa y Miguel domina TS.
- Decisión: `services/ai` (FastAPI) + `apps/web` (Next.js, BFF proxy fino). Contrato OpenAPI como fuente de verdad.
- Alternativas: solo Python + HTMX; SPA estática servida por FastAPI; Gradio/Streamlit.
- Consecuencias: Node en runtime; se mitiga con `make dev` único. Confianza: media.

## ADR-002 shadcn/ui sobre Base UI (2026-10-31)
- Decisión de Miguel (t172). Tokens CSS → primitivos → componentes de dominio. Sin Storybook.

## ADR-003 Orquestación: mise + pnpm workspace + uv + scripts Python (2026-10-31) — DECIDIDO (Miguel, t175)
- Contexto: un comando, reproducible en la máquina del evaluador (Mac/Linux/Windows), sin Docker ni shell.
- Decisión: `mise.toml` fija node 24.22.2, pnpm 10.21.0, python 3.12.16, uv 0.11.17 (`min_version = 2026.10.21` por los arreglos de Ctrl-C en Windows). Tareas mínimas (`setup/start/dev/check/test/build/gen-client`), cada una un único comando que llama a `scripts/<x>.py` (stdlib). Toda la lógica de procesos vive en `scripts/dev.py`.
- Alternativas descartadas: Turborepo/Nx/moon (orquestan JS; no gestionan Python ni procesos de larga vida; más configuración que valor con 2 paquetes); just/Taskfile (otro binario, y las recetas son shell: dependen de cmd/bash); honcho/concurrently (no ordenan health checks; concurrently añade Node en el camino crítico y .cmd en Windows); Docker (Metal no llega al contenedor en Mac: LLM mucho más lento; además pide Docker Desktop al evaluador); Makefile (no nativo en Windows; queda como plan B en `_trash/`).
- Consecuencias: el evaluador instala mise (1 binario). Plan B sin mise documentado (`uv run ... scripts/dev.py`).
- Verificado [V] en macOS: arranque de 5 procesos con health checks en orden; puerto ocupado → error claro y código 2; Ctrl-C (SIGINT) cierra todo en ~1 s sin puertos ni procesos huérfanos (lsof/pgrep), con llama-server real y con `fake_llama`; `setup` descarga llama.cpp b12020 y comprueba SHA256; `check` verde.
- Inferencia [I], no probada: comportamiento en Windows (CTRL_BREAK + `taskkill /T /F` a los 5 s), VC++ runtime, Python de uv con `enable_load_extension` en Windows, Linux. Si `dev.py` muere por SIGKILL, los hijos quedan huérfanos (no usamos Job Objects; `atexit` solo cubre salidas normales).
- Confianza: alta en macOS, media en Windows.

## ADR-004 llama.cpp fijado por tag y SHA256 (2026-10-31)
- `releases/latest` devuelve v0.8.0 sin binarios [V]. Se fija `b12020`; URL directa del asset por SO/arquitectura (sin API) y SHA256 de los 6 assets en `scripts/assets.json` (tomados del campo `digest` de la API de GitHub [V]). CPU por defecto en Windows. Modelos con URL de Hugging Face y SHA256 (coinciden con el etag del Hub [V]).

## ADR-005 Arreglos sobre la salida de los ayudantes (2026-10-31)
- El scaffold web importaba `cn` del paquete npm `cn` (dependencia ajena e innecesaria): sustituido por `clsx + tailwind-merge` local, como en shadcn. `typecheck` ahora hace `next typegen` (LayoutProps). Lockfile único en la raíz (pnpm workspace). `embeddings.dim` corregido a 1024 (bge-m3).
- El servicio IA migrado tiene 29 tests frente a 81 del slice: falta auditar qué tests no se migraron (eval excluida a propósito).
