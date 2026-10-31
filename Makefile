# Único punto de entrada (sustituible por otra herramienta de monorepo más adelante).
.PHONY: setup dev check test build gen-client
setup:      ## dependencias (uv + pnpm workspaces)
	cd services/ai && uv sync
	pnpm install
dev:        ## servicio IA + web con un comando
	./scripts/dev.sh
test:       ## tests Python
	cd services/ai && uv run pytest -q
gen-client: ## openapi.json -> cliente TS
	cd services/ai && uv run python -m doc_assistant.export_openapi
	pnpm --filter web gen:api
build:      ## build de producción de la web
	pnpm --filter web build
check:      ## lint, tipos, tests, drift del contrato
	./scripts/check.sh
