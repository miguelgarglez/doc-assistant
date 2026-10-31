# Doc Assistant — consultas sobre PDFs técnicos y facturas, 100 % local

> Esqueleto vivo: se completará con el flujo extremo a extremo y la evidencia.

## Arranque (idéntico en macOS, Linux y Windows)
1. Instala mise: `curl https://mise.run | sh` (macOS/Linux) o `winget install jdx.mise` (Windows). **Abre una terminal nueva** después.
2. `mise install` (node, pnpm, python y uv en versiones fijadas).
3. `mise run setup` (dependencias, llama-server `b12020` y modelos GGUF, todo verificado con SHA256; ~4 GB).
4. `mise run start` y abre http://127.0.0.1:3000. Ctrl-C cierra todo.

Sin mise (con uv y node ya instalados): `uv run --project services/ai python scripts/setup.py` y `uv run --project services/ai python scripts/dev.py`.

Notas:
- Si ya tienes los modelos, `DOC_ASSISTANT_MODELS_DIR=/ruta/a/models` evita redescargarlos.
- Windows: descomprime en una ruta corta y sin espacios (p. ej. `C:\doc-assistant`). Si `llama-server` dice que falta `VCRUNTIME140.dll`, instala https://aka.ms/vs/17/release/vc_redist.x64.exe. Defender hace la instalación más lenta, no la rompe.
- Si `mise install` falla con 403 / rate limit de GitHub, define `GITHUB_TOKEN` o reinténtalo.
- Plan de contingencia en Windows: WSL2 con Ubuntu y los pasos de Linux tal cual (`http://localhost:3000` funciona desde Windows).
- Todo escucha en `127.0.0.1`; nada sale de la máquina.

## Probado en
macOS (Apple Silicon, M4 16 GB). Windows: no probado en equipo real; el workflow de CI `cross-platform.yml` ejecuta un smoke test (aún no lanzado). Linux: solo vía CI (aún no lanzado).

Limitación conocida: `sqlite-vec` 0.1.9 no publica wheel para Windows ARM; ahí se usaría Python x64 emulado (fallback numpy documentado, no implementado).

## Comandos de desarrollo
`mise run dev` (next dev) · `mise run check` (lint, tipos, tests, drift del contrato, build) · `mise run test` · `mise run gen-client`.

Más: [arquitectura](docs/architecture.md) · [escalado y despliegue](docs/scaling-deployment.md) · [decisiones](docs/decisions-log.md) · [estructura](docs/repo-structure.md).
