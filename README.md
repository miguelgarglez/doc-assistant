# Doc Assistant — consultas sobre documentación técnica y facturas, 100 % local

Pregunta en español sobre fichas técnicas, manuales de instalación, de célula o de visión, y sobre facturas. Cada respuesta cita el documento, la sección, la página y el fragmento exacto, que se ve resaltado junto a la imagen de la página. Si no hay evidencia, el sistema lo dice y no inventa nada. Las facturas (PNG/JPG) se extraen a campos, se comprueba que los importes cuadren (suma e IVA) y se pueden consultar.

## Arranque (igual en macOS, Linux y Windows)
1. Instala mise: `curl https://mise.run | sh` (macOS/Linux) o `winget install jdx.mise` (Windows). **Abre una terminal nueva** después.
2. `mise install` (node, pnpm, python y uv en versiones fijadas).
3. `mise run setup`: dependencias, llama-server `b12020` y modelos GGUF, todo verificado con SHA256.
4. `mise run start` y abre http://127.0.0.1:3000. Ctrl-C cierra todo.

**Internet:** hace falta una vez, para `mise install` y para las dependencias de Python y npm que instala `setup` (`uv sync`, `pnpm install`). Si usas el ZIP de entrega, los modelos (`models/`) y los binarios de llama.cpp (`vendor/archives/`) ya vienen dentro, y `setup` no los descarga. Si usas el repo, los descarga (~4 GB) y pide confirmación. La inferencia es 100 % local: todo escucha en `127.0.0.1`.

**Facturas (OCR):** GLM-OCR en GGUF (`models/GLM-OCR-Q8_0.gguf` + `mmproj-GLM-OCR-Q8_0.gguf`, ~1,4 GB) servido por el mismo llama.cpp en `127.0.0.1:8084`; viene en el ZIP y `mise run setup` lo descarga con SHA256. Alternativa documentada: `DOC_ASSISTANT_OCR_RUNTIME=ollama` usa [Ollama](https://ollama.com) con `ollama pull glm-ocr` en `:11434`.

Sin mise (con uv y node ya instalados): `uv run --project services/ai python scripts/setup.py` y `uv run --project services/ai python scripts/dev.py`.

### Notas
- Si ya tienes los modelos: `mise run setup --models-dir /ruta/a/models` (o `DOC_ASSISTANT_MODELS_DIR=/ruta`). `setup` comprueba lo que hay (el tamaño, y el SHA256 con `--verify`) y solo descarga lo que falte, con reanudación. La ruta se guarda en `.env.local`. Orden de resolución: `--models-dir` > `DOC_ASSISTANT_MODELS_DIR` > `.env.local` > `./models`. Si va a descargar más de 1 GB pide confirmación (`--yes` en CI).
- Windows:
  - Descomprime en una ruta corta y sin espacios (p. ej. `C:\docassist`).
  - Si falta `VCRUNTIME140.dll`, instala https://aka.ms/vs/17/release/vc_redist.x64.exe.
  - Si `mise install` da 403 por rate limit de GitHub, define `GITHUB_TOKEN`.
  - Contingencia: WSL2 con Ubuntu y los pasos de Linux.

## Probado en
macOS (Apple Silicon, M4 16 GB). Windows: no probado en un equipo real; el workflow `cross-platform.yml` ejecuta un smoke test, pero aún no se ha lanzado. Linux: solo vía ese CI. Limitación: `sqlite-vec` no publica wheel para Windows ARM.

## Huecos del enunciado
Decisiones sobre lo que el enunciado deja abierto: [docs/open-gaps.md](docs/open-gaps.md). Cobertura requisito a requisito: [docs/requirements-coverage.md](docs/requirements-coverage.md).

## Evidencia
- `evidence/screenshots/`: capturas Playwright de consulta, rechazo, error y facturas, en escritorio y móvil.
- `evidence/live/results.md`: corrida real con documentos y facturas **sintéticos** (`evidence/fixtures`).
- Regenerar: `mise run evidence` (capturas) y `mise run evidence --live` (corrida real; necesita los modelos).

No es la evaluación final: no se han usado documentos ni facturas reales.

## Desarrollo
- `mise run dev`: next dev.
- `mise run check`: lint, tipos, tests, deriva del contrato OpenAPI→TS y build.
- `mise run test`.
- `mise run gen-client`.
- `mise run package`: ZIP de entrega, probado en limpio.

Más: [arquitectura](docs/architecture.md) · [escalado y despliegue](docs/scaling-deployment.md) · [decisiones](docs/decisions-log.md) · [estructura](docs/repo-structure.md) · [revisión](docs/reviews/2026-10-31-sol.md) · [NOTICE](NOTICE).
