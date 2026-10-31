#!/usr/bin/env bash
# CI local: lint, tipos, tests y drift del contrato OpenAPI -> cliente TS.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/ai"
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q
uv run python -m doc_assistant.export_openapi
cd "$ROOT/apps/web"
pnpm gen:api && git -C "$ROOT" diff --exit-code -- services/ai/openapi.json apps/web/src/lib/api/schema.d.ts
pnpm lint && pnpm typecheck && pnpm build
echo "check OK"
