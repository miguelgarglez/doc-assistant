#!/usr/bin/env bash
# Arranque único: servicio IA (FastAPI) + web (Next). Ctrl-C para todo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AI_PORT="${AI_PORT:-8000}"; WEB_PORT="${WEB_PORT:-3000}"
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd "$ROOT/services/ai" && uv run uvicorn doc_assistant.api:app --host 127.0.0.1 --port "$AI_PORT") & pids+=($!)
for _ in $(seq 1 60); do curl -fsS "http://127.0.0.1:$AI_PORT/health" >/dev/null && break; sleep 1; done
curl -fsS "http://127.0.0.1:$AI_PORT/health" >/dev/null || { echo "servicio IA no responde" >&2; exit 1; }
(cd "$ROOT/apps/web" && AI_SERVICE_URL="http://127.0.0.1:$AI_PORT" pnpm exec next ${WEB_MODE:-dev} -p "$WEB_PORT") & pids+=($!)
echo "Listo: http://127.0.0.1:$WEB_PORT"
wait -n
