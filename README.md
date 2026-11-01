# Doc Assistant — consultas sobre documentación técnica y facturas, 100 % local

Pregunta en español sobre fichas técnicas, manuales de instalación, de célula o de visión, y sobre facturas. Cada respuesta cita el documento, la sección, la página y el fragmento exacto, que se ve resaltado junto a la imagen de la página. El servicio rechaza respuestas cuando sus verificaciones no encuentran evidencia suficiente. Estas comprobaciones son heurísticas y no garantizan la ausencia de errores. Las facturas (PNG/JPG) se extraen a campos, se comprueba que los importes cuadren (suma e IVA) y se pueden consultar.

## Arranque (igual en macOS, Linux y Windows)
1. Instala mise: `curl https://mise.run | sh` (macOS/Linux) o `winget install jdx.mise` (Windows). **Abre una terminal nueva** después.
2. `mise install` (node, pnpm, python y uv en versiones fijadas).
3. `mise run setup`: dependencias, llama-server `b12020` y modelos GGUF, todo verificado con SHA256.
4. `mise run start` y abre http://127.0.0.1:3000. Ctrl-C cierra todo.

**Internet:** hace falta una vez, para `mise install` y para las dependencias de Python y npm que instala `setup` (`uv sync`, `pnpm install`). Si usas el ZIP de entrega, los modelos (`models/`) y los binarios de llama.cpp (`vendor/archives/`) ya vienen dentro, y `setup` no los descarga. Si usas el repo, los descarga (~4 GB) y pide confirmación. La inferencia es 100 % local: todo escucha en `127.0.0.1`.

**Facturas (OCR):** GLM-OCR en GGUF (`models/GLM-OCR-Q8_0.gguf` + `mmproj-GLM-OCR-Q8_0.gguf`, ~1,4 GB) servido por el mismo llama.cpp en `127.0.0.1:8084` (`DOC_ASSISTANT_OCR_PORT`); viene en el ZIP y `mise run setup` lo descarga con SHA256. Alternativa documentada: `DOC_ASSISTANT_OCR_RUNTIME=ollama` usa [Ollama](https://ollama.com) con `ollama pull glm-ocr` en `:11434`.

Sin mise (con uv y node ya instalados): `uv run --project services/ai python scripts/setup.py` y `uv run --project services/ai python scripts/dev.py`.

### Puertos
Por defecto: web 3000, servicio de IA 8000 y modelos 8081 (lenguaje), 8082 (embeddings), 8083 (reranker) y 8084 (OCR). Cada uno se cambia con una variable de entorno; `config/config.yaml` lee las mismas, así que el arranque y el servicio no pueden discrepar.

| Pieza | Variable | Por defecto |
|---|---|---|
| Web | `DOC_ASSISTANT_WEB_PORT` | 3000 |
| Servicio de IA | `DOC_ASSISTANT_AI_PORT` | 8000 |
| Modelo de lenguaje | `DOC_ASSISTANT_LLM_PORT` | 8081 |
| Embeddings | `DOC_ASSISTANT_EMBEDDINGS_PORT` | 8082 |
| Reranker | `DOC_ASSISTANT_RERANKER_PORT` | 8083 |
| OCR de facturas | `DOC_ASSISTANT_OCR_PORT` | 8084 |

Ejemplo: `DOC_ASSISTANT_LLM_PORT=8181 DOC_ASSISTANT_WEB_PORT=3170 mise run start`. En PowerShell: `$env:DOC_ASSISTANT_LLM_PORT=8181; mise run start`.

Si un puerto está ocupado, `start` no arranca nada y sale con código 2. El mensaje dice qué puerto es, cómo ver quién lo usa (`lsof` o `netstat`) y qué variable cambiar, con un puerto libre sugerido. Un valor que no es un puerto, o dos piezas con el mismo puerto, también se rechazan antes de arrancar. `mise run package` (prueba en limpio) y `mise run evidence --live` usan las mismas variables y comprueban los mismos puertos.

### Notas
- Si ya tienes los modelos: `mise run setup --models-dir /ruta/a/models` (o `DOC_ASSISTANT_MODELS_DIR=/ruta`). `setup` comprueba lo que hay (el tamaño, y el SHA256 con `--verify`) y solo descarga lo que falte, con reanudación. La ruta se guarda en `.env.local`. Orden de resolución: `--models-dir` > `DOC_ASSISTANT_MODELS_DIR` > `.env.local` > `./models`. Si va a descargar más de 1 GB pide confirmación (`--yes` en CI).
- Windows:
  - Descomprime en una ruta corta y sin espacios (p. ej. `C:\docassist`).
  - Si falta `VCRUNTIME140.dll`, instala https://aka.ms/vs/17/release/vc_redist.x64.exe.
  - Si `mise install` da 403 por rate limit de GitHub, define `GITHUB_TOKEN`.
  - Contingencia: WSL2 con Ubuntu y los pasos de Linux.

## Probado en
macOS 26.6.2 (build 25G83), Apple M4, CPU de 10 núcleos, GPU de 10 núcleos y 16 GiB de memoria unificada. Datos consultados con `sysctl -n machdep.cpu.brand_string hw.physicalcpu hw.logicalcpu hw.memsize`, `sw_vers` y `system_profiler SPDisplaysDataType` el 1 de noviembre de 2026. La memoria unificada es compartida; no se ha medido la memoria ocupada por los modelos. Windows y Linux no se han probado en este equipo ni se ha ejecutado todavía el workflow `cross-platform.yml`. Limitación: `sqlite-vec` no publica wheel para Windows ARM.

La [revisión de portabilidad](docs/portabilidad.md) recoge los sistemas y arquitecturas aún sin probar, y los límites de los scripts.

## Huecos del enunciado
Decisiones sobre lo que el enunciado deja abierto: [docs/open-gaps.md](docs/open-gaps.md). Cobertura requisito a requisito: [docs/requirements-coverage.md](docs/requirements-coverage.md).

## Evidencia
- `evidence/screenshots/`: capturas Playwright de consulta, rechazo, error y facturas, en escritorio y móvil.
- `evidence/live/results.md`: corrida real con documentos y facturas **sintéticos** (`evidence/fixtures`).
- Regenerar: `mise run evidence` (capturas) y `mise run evidence --live` (corrida real; necesita los modelos).

No es la evaluación final: no se han usado documentos ni facturas reales.

## Desarrollo
- `mise run dev`: next dev.
- `mise run check`: lint, tipos, tests normales, enlaces Markdown, deriva del contrato OpenAPI→TS y build.
- `mise run test`, `test-unit` y `test-integration`: tests normales por ámbito.
- `mise run test-architecture`: límites de imports del servicio.
- `mise run test-live`: batería optativa con un modelo real.
- `mise run check-links`: destinos locales de los Markdown.
- `mise run gen-client`.
- `mise run package`: ZIP de entrega, probado en limpio.

Más: [índice de documentación](docs/README.md).
