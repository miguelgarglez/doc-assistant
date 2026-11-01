# Estructura del repo
```text
mise.toml                  versiones fijadas y tareas de un solo comando
config/config.yaml         configuración validada del servicio
scripts/
  check.py                 lint, tipos, tests, enlaces, contrato y build
  check_links.py           enlaces locales de Markdown, solo biblioteca estándar
  setup.py, dev.py         instalación y arranque coordinado
  package.py               ZIP64 y prueba al descomprimir
  evidence.py              capturas y corrida live con fixtures
  fake_llama.py            servicios de modelo simulados para CI
  tests/                   pruebas de las herramientas
services/ai/
  src/doc_assistant/
    api/                    rutas, esquemas y traducción SSE
    application/            casos de uso, coordinación y puertos
    domain/                 reglas y valores sin E/S
    infra/                  SQLite, archivos, PDF y clientes HTTP
    bootstrap.py            composición y ciclo de vida
    config.py               carga y validación de configuración
    export_openapi.py       entrada de exportación del contrato
  tests/
    unit/                   reglas aisladas
    integration/            SQLite, PDF y HTTP local
    live/                   modelos y servicios reales optativos
  openapi.json             fuente de verdad del contrato
apps/web/
  src/app/                 rutas Next, layout y proxy fino
  src/features/            chat, sources, uploads, history, viewer y system
  src/components/          shell, tema, UI y AI Elements compartidos
  src/lib/                 cliente API, tipos y utilidades compartidas
  eslint-rules/            límite entre APIs públicas de features
.github/workflows/ci.yml   mismo control local y Playwright con servicios falsos
.github/workflows/cross-platform.yml
                           smoke manual para Windows, Linux y macOS
docs/                      índice, arquitectura, ADR, cobertura y revisiones
evidence/                  capturas y resultados sintéticos
```

El [índice documental](README.md) explica qué pregunta responde cada documento. Los diseños de multiusuario e historial son propuestas; su presencia en `docs/design/` no implica implementación.

## Reestructuración v0.18

**Estado: ejecutada.** La reorganización conserva el comportamiento, el contrato OpenAPI y el cliente generado. El árbol anterior describe el estado actual.

### Resultado y límites

La ejecución eliminó el ciclo entre API e historial y borró `adapters.py`. Los protocolos viven con sus consumidores en `application/ports`, los clientes HTTP en `infra/models`, los dobles en tests y las factorías de la aplicación HTTP en `bootstrap.py`. Facturas conserva una sola transacción para la fila, los fragmentos, FTS, vectores y la página.

`doc_assistant` sigue siendo el paquete instalable. `bootstrap.py` conecta la aplicación HTTP y crea su objeto FastAPI. `history_clear.py`, `feedback_export.py` y `feedback_review.py` conservan entradas de línea de comandos independientes. Las dos entradas de feedback abren el almacén SQLite que necesitan; `history_clear.py` usa la API local.

```text
services/ai/src/doc_assistant/
  api/                 rutas, esquemas HTTP y serialización SSE
  application/         casos de uso, puertos y coordinación
  domain/              reglas y valores sin E/S
  infra/               sqlite, archivos, modelos HTTP, OCR y PDF
  bootstrap.py         composición y configuración de la aplicación
  config.py            carga y validación de configuración
  export_openapi.py    entrada de exportación del contrato
apps/web/src/
  app/                 rutas Next y proxy HTTP
  features/            chat, sources, uploads, history, viewer, system
  components/          shell, ui y componentes compartidos
  lib/                 cliente API, utilidades y tipos compartidos
```

Las flechas de importación apuntan hacia el interior. `domain` no importa otras capas ni FastAPI, SQLite, HTTP o configuración de entorno. `application` importa `domain` y sus propios puertos; no importa `api` ni `infra`. `infra` implementa puertos de `application` y puede importar `domain`, pero no `api`. `api` importa `application` y `domain`, nunca `infra`. `bootstrap` puede importar todas las capas y las conecta mediante inyección. `config` se carga en composición y se traduce a valores estrechos. Los esquemas HTTP permanecen en `api`. El test de arquitectura controla las cuatro capas y limita los módulos raíz a una lista cerrada de entradas y configuración.

`tests/unit/test_architecture.py` usa `ast` de la biblioteca estándar. Resuelve imports absolutos y relativos, incluidos los de `__init__.py`, inspecciona imports dentro de funciones y bajo `TYPE_CHECKING`, rechaza imports dinámicos internos y comprueba dependencias indirectas y ciclos. Sus casos de aceptación incluyen ejemplos permitidos y prohibidos. Las reglas de las cuatro capas no tienen excepciones; las entradas raíz permitidas se enumeran en `ROOT_ENTRIES`.

### Mapa aplicado del servicio IA

Cada fila registra el destino de los módulos anteriores a v0.18.

| Módulo anterior | Destino actual y responsabilidad |
| --- | --- |
| `__init__.py` | Raíz del paquete, metadatos mínimos. |
| `api.py` | `api/schemas.py`, `api/routes.py`, `api/streaming.py` y `bootstrap.py`. |
| `history_api.py` | `api/history.py`, con dependencias recibidas desde composición. |
| `history_stream.py` | `api/history_stream.py` y `api/streaming.py`, con el productor de eventos inyectado. |
| `history_contract.py` | `application/ports/history.py` y tipos de aplicación. |
| `history.py` | `infra/history/sqlite.py`, detrás del puerto de historial. |
| `history_outbox.py` | `application/history/outbox.py` para coordinación e `infra/history/` para persistencia concreta. |
| `history_clear.py` | Entrada CLI raíz conservada; ejecuta el borrado mediante la API local. |
| `feedback_export.py`, `feedback_review.py` | Entradas CLI raíz conservadas; abren el almacén SQLite de historial. |
| `ask.py`, `ask_capacity.py` | `application/ask/` para consulta y capacidad; traducción SSE en `api/`. |
| `ingest.py`, `ingest_jobs.py` | `application/ingest/` para coordinación y trabajos; archivos y PDF en `infra/`. |
| `sources.py` | `application/sources.py`; acceso al índice mediante puerto. |
| `invoices.py` | `application/invoices/` para casos de uso, `infra/invoices/` para SQLite y archivos, `domain/invoices/` para reglas puras. |
| `invoice_blocks.py`, `invoice_fields.py`, `invoice_index.py` | `domain/invoices/` para valores y transformaciones puras; índice concreto en `infra/invoices/index.py`. |
| `invoice_extract.py`, `invoice_query.py` | `application/invoices/` para extracción y consulta; proveedores detrás de puertos. |
| `answer_markup.py`, `inline.py`, `verifier.py` | `domain/answers/` para validación y transformaciones puras. |
| `chunking.py`, `partial_json.py` | `domain/documents/chunking.py` y `domain/answers/partial_json.py`. |
| `meta.py` | `application/answers/meta.py`; reglas puras a `domain/answers/`. |
| `highlight.py`, `pdf_lock.py` | `infra/pdf/`, detrás de puertos de aplicación cuando cruza de capa. |
| `store.py` | `infra/storage/chunks.py`; protocolos en `application/ports/`. |
| `adapters.py` | `application/ports/` para protocolos y errores; `infra/models/` para HTTP; dobles en tests y factorías en composición. |
| `health.py` | `application/health.py` para coordinación, sondas en `infra/`, esquemas de respuesta en `api/`. |
| `config.py` | Raíz `config.py`, usada por composición y traducida a valores de aplicación. |
| `export_openapi.py` | Entrada CLI raíz, importando composición y conservando ruta y formato. |

### Web, scripts y pruebas

En web, `app/` conserva rutas, layout y proxy. `features/chat`, `sources`, `uploads`, `history`, `viewer` y `system` agrupan sus componentes, hooks, estado y lógica. El ensamblaje de proveedores queda en `app/`. `components/shell`, `components/theme`, `components/ui` y `components/ai-elements` son compartidos. `lib/api` conserva transporte, tipos generados y errores comunes. Una feature solo accede a otra mediante su `index.ts`; `eslint-rules/feature-boundaries.mjs` comprueba imports estáticos y dinámicos, y su test cubre casos permitidos y prohibidos.

`scripts/` mantiene las entradas multiplataforma `setup`, `dev`, `check`, `package`, `evidence`, `evolution` y `fake_llama`, con `_common.py` compartido y `assets.json` como inventario. `check_links.py` valida con la biblioteca estándar los destinos locales de los Markdown. Sus tests viven en `scripts/tests/`. El ciclo de vida de procesos no cambia; las operaciones de parada se limitan a procesos iniciados por el lanzador.

Los tests del servicio se clasifican por alcance. `services/ai/tests/unit/` contiene 126 casos de reglas aisladas, `integration/` contiene 280 casos con SQLite, PDF o HTTP local, y `live/` contiene 35 casos optativos para un modelo real. `conftest.py`, `doubles.py`, `markup.py` e `invoice_battery_support.py` compartidos quedan en la raíz. Los e2e permanecen en `apps/web/e2e/`. Los cuatro casos de `live.spec.ts` requieren `LIVE_BASE_URL` y se omiten en la suite simulada.

`mise.toml` es la interfaz de tareas con versiones fijadas. `test-unit`, `test-integration`, `test-live` y `test-architecture` exponen cada ámbito. `scripts/check.py` ejecuta las suites normales y no activa live aunque exista una URL de modelo en el entorno. CI ejecuta el mismo control local y Playwright con servicios falsos. El workflow multiplataforma sigue siendo manual hasta verificarlo en sus plataformas. La reorganización no añade dependencias.

### Revisión de herramientas de mantenibilidad

La revisión conserva controles que detectan un fallo concreto y que se ejecutan con los comandos existentes:

- `ast` comprueba la dirección de los imports, las dependencias transitivas y los ciclos del servicio.
- La regla local de ESLint comprueba que cada feature web use la entrada pública de las demás. Su test cubre imports estáticos, relativos, `require`, imports dinámicos literales y un destino dinámico desconocido.
- Las tareas de `mise` separan tests unitarios, de integración, live y de arquitectura sin duplicar la lógica de ejecución.
- `check_links.py` comprueba los destinos locales de los Markdown. Usa solo la biblioteca estándar y tiene tests propios; no valida anclas.
- CI ejecuta `mise run check` y los e2e con los mismos puntos de entrada que el entorno local.

No se añaden `import-linter`, analizadores de complejidad ni detectores de código muerto. No se ejecutó una evaluación de `vulture`, `knip` o herramientas equivalentes, por lo que esta revisión no afirma que el árbol carezca de código muerto ni aporta una métrica de complejidad. Incorporarlas exige definir primero un defecto o un umbral que haga fallar el check. El test AST y la regla de ESLint sí responden a los dos límites estructurales de esta reorganización.

### Riesgos y controles vigentes

- **Contrato y streaming.** El check regenera OpenAPI y el cliente, y los compara con git. Los tests de streaming cubren el orden y el resultado final.
- **Ciclos y composición.** El test AST comprueba el grafo directo y transitivo, los ciclos y los imports dinámicos internos.
- **Persistencia y concurrencia.** Las pruebas de historial, almacenamiento, outbox y PDF cubren los límites transaccionales y el bloqueo compartido.
- **Entradas y empaquetado.** Uvicorn, el exportador y los comandos documentados apuntan a `bootstrap.py` o a las entradas raíz conservadas. El empaquetado no cambió.
- **Imports y estado en web.** La regla de ESLint protege las APIs públicas entre features. Los e2e cubren chat, subidas, fuentes e historial.
- **Cobertura aparente.** La clasificación comparó la colección antes y después. Los tests live siguen separados porque requieren modelos reales.

Los documentos de [arquitectura](architecture.md), [streaming](streaming.md) y [portabilidad](portabilidad.md) describen las restricciones actuales. El [diseño de historial](design/persistencia-historial-feedback.md) recoge decisiones y propuestas relacionadas. Actualizar esos enlaces y documentos cuando cambien las rutas efectivas.

### Ejecución y controles

La reorganización se ejecutó en unidades pequeñas. Cada unidad terminó con `mise run check`, `CI=1 pnpm --filter web e2e` y una comparación de `services/ai/openapi.json` y `apps/web/src/lib/api/schema.d.ts` contra `56b1967`.

1. Se rompió el ciclo entre API e historial y se dividieron protocolos, clientes, dobles y factorías.
2. Se movieron composición, transporte, puertos, persistencia, casos de uso y dominio. La escritura de factura, fragmentos, FTS, vectores y página conserva una conexión, un `commit` y un `rollback`.
3. Se activó el test AST sobre todo `doc_assistant`, sin excepciones.
4. Se movieron seis features web y se activó la regla ESLint de APIs públicas.
5. Se clasificaron 441 casos sin perder ninguna de las 272 funciones recogidas justo antes de la clasificación.
6. Se añadieron tareas por ámbito y el control de enlaces Markdown a `mise run check` y CI.

El contrato OpenAPI y el cliente generado siguen idénticos a `56b1967`. La comprobación final pasa 406 tests normales del servicio, 28 de scripts y 215 e2e; 35 casos live requieren un modelo y cuatro e2e requieren el stack live. No hubo cambios visuales, por lo que no se generaron capturas antes y después.
