# CHECKPOINT

## Hitos
- **31-oct 12:10 (Madrid) · Estructura creada.** Monorepo con dos piezas: el servicio de IA en Python y la web en Next.js. Cada decisión queda en `docs/decisions-log.md`.
- **31-oct ~12:50 · Servicio IA y web base unidos.** Codex migró el núcleo del slice a FastAPI (29 tests verdes, tipos estrictos). Cursor montó la web con shadcn sobre Base UI y los 6 componentes de dominio con datos de ejemplo. Corregí dos fallos suyos (un paquete npm ajeno llamado `cn` y el typecheck).
- **31-oct ~13:20 · Arranque unificado verificado.** `mise run start` levanta los 3 llama-server, el servicio IA y la web, en orden y con comprobación de salud. Ctrl-C lo cierra todo en ~1 s sin dejar procesos ni puertos (comprobado con lsof). Puerto ocupado da un error claro. Windows queda preparado (CI listo, sin ejecutar) pero no probado.
- **31-oct ~13:20 · Contrato.** `openapi.json` sale del servicio; los tipos TS se generan de él y `mise run check` falla si no están al día.

## Sigue
1. Auditar 29 vs 81 tests del slice. 2. Cliente TS tipado (openapi-fetch) en la página. 3. E2E con un PDF del kit (sin commitearlo). 4. Facturas. 5. Revisión independiente (sol). 6. architecture.md / scaling-deployment.md.

## Comandos
`mise install && DOC_ASSISTANT_MODELS_DIR=<carpeta de modelos> mise run setup` · `mise run start` · `mise run check` · `DOC_ASSISTANT_FAKE_LLAMA=1 mise run start` (sin modelos)
