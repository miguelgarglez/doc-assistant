.PHONY: setup dev check
setup:   ## instala dependencias (uv + pnpm)
	cd services/ai && uv sync
	cd apps/web && pnpm install
dev:     ## arranca servicio IA + web
	./scripts/dev.sh
check:   ## lint, tipos, tests, drift del contrato
	./scripts/check.sh
