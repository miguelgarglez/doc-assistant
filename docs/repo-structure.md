# Estructura del repo
```
mise.toml            herramientas fijadas + tareas (1 comando cada una)
package.json         raíz del pnpm workspace (packageManager fijado)
pnpm-workspace.yaml  apps/*
config/config.yaml   config del servicio IA (validada con Pydantic al arrancar)
scripts/
  _common.py         rutas/plataforma compartidas
  assets.json        llama.cpp b12020 + modelos, con SHA256
  setup.py           uv sync, pnpm install, build, llama-server, modelos
  dev.py             arranque único: LLM, embeddings, reranker, OCR → IA → web; Ctrl-C limpio
  check.py           ruff, mypy, pytest, contrato sin drift, eslint, tsc, build
  fake_llama.py      simula llama-server (CI)
  package.py         ZIP64 de entrega + smoke al descomprimir
  evidence.py        capturas e2e; --live corrida real con fixtures
  evolution.py       galería por tag (evidence/evolution)
NOTICE               licencias de modelos y llama.cpp
services/ai/
  src/doc_assistant/ FastAPI: api, ask, verifier, ingest, chunking,
                     store (SQLite+sqlite-vec), invoices, adapters (puertos), config
                     invoice_blocks (fichas y tablas), ask_capacity (cola por proceso),
                     pdf_lock (acceso serializado a PDFium)
  openapi.json       contrato (fuente de verdad)
apps/web/            Next.js 16 + TS strict
  src/app/api/[...path]/route.ts   proxy fino → servicio IA (BFF)
  src/lib/api/schema.d.ts          tipos generados desde openapi.json
  src/components/ui/               primitivos shadcn sobre Base UI
  src/components/chat/             respuestas, bloques, citas, aclaraciones y visor
  src/features/viewer/             página y resaltado
  src/components/uploads/          diálogo y avisos de subida
  src/features/sources/            gestión de fuentes
  src/features/system/             estado de componentes y última traza
  src/components/ai-elements/      componentes de conversación
  src/components/providers/        estado compartido de chat y subidas
  src/lib/domain/                  tipos y utilidades de dominio
  src/lib/chat/                    transporte SSE, vistas y validación de bloques
.github/workflows/cross-platform.yml   smoke Win/Linux/Mac (no ejecutado)
docs/                README (índice), ADRs, CHECKPOINT, CHANGELOG, versioning, architecture, scaling,
                     requirements-coverage, open-gaps, design/, evolution-notes/, reviews/
evidence/            screenshots/, live/, fixtures/ (sintéticos), evolution/ (por tag),
                     comparison-*/, evaluacion-sintetica/, chunking/, modelos/
vendor/, models/     binarios, archives/ y GGUF (git-ignorados)
_trash/              en vez de borrar (git-ignorado)
```

El [índice documental](README.md) explica qué pregunta responde cada documento. Los diseños de multiusuario e historial son propuestas; su presencia en `docs/design/` no implica implementación.

## Propuesta de reestructuración v0.18

**Estado: propuesta para revisión.** La fase 1 no mueve código ni modifica contratos. El objetivo es facilitar cambios locales y hacer comprobables las dependencias. La estructura actual descrita arriba sigue vigente hasta que se apruebe y ejecute el plan.

### Diagnóstico y límites

`api.py` define esquemas, rutas, streaming y composición. `history_api.py` y `history_stream.py` importan `api.py`, que a su vez importa módulos de historial. `adapters.py` mezcla protocolos, implementaciones HTTP, dobles y factorías. `invoices.py` combina persistencia, ingesta y respuestas. `store.py` usa configuración y adaptadores concretos. Estas relaciones exigen separar responsabilidades antes de imponer una dirección de imports. Cambiar únicamente los nombres de directorios conservaría esos acoplamientos.

La propuesta mantiene `doc_assistant` como paquete instalable y conserva los puntos de entrada externos hasta actualizar sus consumidores en el mismo paso. La composición queda en `bootstrap.py`, único lugar que conecta implementaciones concretas con puertos y crea la aplicación. Los nombres del árbol son destinos propuestos, no archivos existentes.

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

Las flechas de importación apuntan hacia el interior. `domain` no importa otras capas ni FastAPI, SQLite, HTTP o configuración de entorno. `application` importa `domain` y sus propios puertos; no importa `api` ni `infra`. `infra` implementa puertos de `application` y puede importar `domain`, pero no `api`. `api` importa `application` y `domain`, nunca implementaciones de `infra`. `bootstrap` puede importar todas las capas y las conecta mediante inyección. `config` se carga en composición y se traduce a parámetros o valores necesarios, sin que dominio lea variables de entorno. Los esquemas HTTP permanecen en `api`; los datos intercambiados con aplicación no dependen de `Request`, `Response` ni eventos FastAPI. Los protocolos viven junto al consumidor en `application/ports`, no junto a su implementación.

Para verificar las reglas se propone un test propio con `ast` de la biblioteca estándar, ejecutado por pytest y CI. Resuelve imports absolutos y relativos, incluidos los de `__init__.py`, e inspecciona imports dentro de funciones y bajo `TYPE_CHECKING`. Rechaza imports dinámicos internos no declarados y comprueba también dependencias indirectas, no solo imports directos. Sus pruebas de aceptación crean ejemplos temporales permitidos y prohibidos, incluido un ciclo. No requiere instalar paquetes. En cada extracción se activa la regla sobre el perímetro migrado; no se admite una lista de excepciones permanente. Antes de ampliar el perímetro se eliminan sus violaciones. La comprobación no demuestra ausencia de acoplamiento por inyección o reflexión, por lo que la revisión de código sigue siendo necesaria.

### Mapa del servicio IA

Cada fila cubre todos los módulos actuales de `services/ai/src/doc_assistant/`. Una flecha con varios destinos implica separar responsabilidades, no duplicar el módulo. Los nombres finales se ajustarán al extraer cada responsabilidad.

| Actual | Destino propuesto y responsabilidad |
| --- | --- |
| `__init__.py` | Raíz del paquete, metadatos mínimos. |
| `api.py` | `api/schemas`, `api/routes`, `api/streaming` y `bootstrap.py`. Extraer composición y rutas por separado; conservar nombres de esquemas OpenAPI. |
| `history_api.py` | `api/routes/history.py`. Recibir dependencias sin importar `api.py`. |
| `history_stream.py` | `application/history/stream.py` y `api/streaming`. Separar registro de eventos de su traducción HTTP. |
| `history_contract.py` | `application/ports/history.py` y tipos de aplicación; separar referencias a outbox. |
| `history.py` | `infra/history/sqlite.py`, detrás del puerto de historial. |
| `history_outbox.py` | `application/history/outbox.py` para coordinación e `infra/history/` para persistencia concreta. |
| `history_clear.py` | `application/history/clear.py`; operaciones concretas en `infra/history/`. |
| `feedback_export.py`, `feedback_review.py` | `application/feedback/` para operaciones; mantener entradas CLI explícitas si tienen consumidores. |
| `ask.py`, `ask_capacity.py` | `application/ask/` para consulta y capacidad. El controlador conserva la traducción SSE. |
| `ingest.py`, `ingest_jobs.py` | `application/ingest/` para coordinación y trabajos; archivos y PDF concretos a `infra/`. |
| `sources.py` | `application/sources.py`; acceso al índice mediante puerto. |
| `invoices.py` | `application/invoices/` para casos de uso, `infra/storage/invoices.py` para SQLite y archivos, `domain/invoices/` para reglas puras. |
| `invoice_blocks.py`, `invoice_fields.py`, `invoice_index.py` | `domain/invoices/` para valores y transformaciones puras; separar cualquier acceso externo. |
| `invoice_extract.py`, `invoice_query.py` | `application/invoices/` para extracción y consulta; proveedores detrás de puertos. |
| `answer_markup.py`, `inline.py`, `verifier.py` | `domain/answers/` para validación y transformaciones puras. |
| `chunking.py`, `partial_json.py` | `domain/documents/chunking.py`, `domain/answers/partial_json.py`; comprobar que sigan sin E/S. |
| `meta.py` | `application/answers/meta.py`; reglas puras a `domain/answers/`. |
| `highlight.py`, `pdf_lock.py` | `infra/pdf/`; exponer resaltado por puerto si lo necesita aplicación. |
| `store.py` | `infra/storage/chunks.py`; extracción de protocolos a `application/ports/`. |
| `adapters.py` | `application/ports/` para protocolos y errores; `infra/models/`, `infra/ocr/` para HTTP; dobles a tests y factorías a composición. `serialize_f32` queda con el almacenamiento que la consume. |
| `health.py` | `application/health.py` para coordinación, sondas en `infra/`, esquemas de respuesta en `api/`. |
| `config.py` | Raíz `config.py`, usada por composición. Aislar valores necesarios para casos de uso. |
| `export_openapi.py` | Raíz como entrada CLI, importando composición. Mantener ruta de salida y formato. |

### Web, scripts y pruebas

En web, `app/` conserva rutas, layout y proxy. Cada `features/<nombre>/` agrupa componentes, hooks, estado y lógica exclusivos de esa funcionalidad. Los actuales `components/chat`, `history`, `sources`, `system`, `uploads` y `viewer`, junto a sus piezas específicas de `lib/` y `hooks/`, pasan a su feature. `components/providers` se reparte por dueño y el ensamblaje de proveedores queda en `app/`. `components/shell`, `components/ui` y `components/ai-elements` permanecen compartidos mientras tengan varios consumidores; los específicos pasan a su feature. `lib/api` conserva transporte, tipos generados y errores compartidos. `lib/domain` solo conserva tipos y funciones usados por varias features; el resto se mueve con su consumidor. `themes/` y estilos globales siguen compartidos. Una feature puede importar `components` y `lib`, pero no internals de otra feature; una colaboración entre features pasa por su API pública o composición en `app`. `components/ui` no importa features. ESLint puede comprobar imports restringidos con la configuración existente; el primer paso de web debe incluir casos permitidos y prohibidos.

`scripts/` mantiene entradas multiplataforma `setup`, `dev`, `check`, `package`, `evidence`, `evolution` y `fake_llama`, con `_common.py` compartido y `assets.json` como inventario. Solo se propone agrupar auxiliares cuando exista un límite claro, manteniendo las rutas de entrada usadas por `mise.toml`, CI y documentación. Sus tests siguen en `scripts/tests/`. No se cambia el ciclo de vida de procesos: las operaciones de parada se limitan a PID propiedad del proceso lanzador.

Los tests del servicio se clasifican por alcance, no por nombre de módulo: `services/ai/tests/unit/` para reglas aisladas, `integration/` para SQLite, PDF y HTTP local, y `live/` para modelos o servicios reales. `conftest.py` y `markup.py` compartidos quedan en la raíz de tests; fixtures específicas quedan junto a su ámbito. Los e2e de navegador permanecen en `apps/web/e2e/`; `live.spec.ts` queda claramente separado de los e2e con mocks. La clasificación se decide tras leer cada test y conserva los escenarios y fixtures. Los tests live son optativos y declaran requisitos; los tests normales y CI no descargan modelos. No se crean suites vacías ni se traslada un test solo por su nombre.

`mise.toml` sigue siendo la interfaz de tareas con versiones fijadas; `scripts/check.py` conserva la lógica portable. CI ejecuta el mismo control local, el test de límites y Playwright con servicios falsos. El workflow multiplataforma sigue siendo manual hasta verificarlo en sus plataformas. Ninguna dependencia nueva se instala sin autorización. El test de imports propuesto evita introducir `import-linter` para esta fase.

### Riesgos y mitigaciones

- **Contrato y streaming.** Extraer modelos Pydantic o rutas puede cambiar nombres, orden o eventos. Comparar OpenAPI y cliente, y ejecutar los tests de streaming en cada paso.
- **Ciclos y composición.** Mover los imports actuales puede trasladar el ciclo de `api` e historial. Extraer primero dependencias inyectadas y verificar el grafo completo.
- **Persistencia y concurrencia.** Cambiar conexiones SQLite, outbox o bloqueo PDF puede alterar datos o sincronización. Mantener esquemas y límites transaccionales y ejecutar las pruebas de historial, store y concurrencia.
- **Entradas y empaquetado.** Uvicorn, el exportador, scripts y distribución pueden depender de rutas actuales. Buscar consumidores antes de cada traslado y verificar arranque, exportación y empaquetado sin instalar nada.
- **Imports y estado en web.** Mover providers puede duplicar estado o romper hidratación. Mantener un único proveedor por ámbito y cubrir chat, subidas e historial con e2e.
- **Cobertura aparente.** Reclasificar tests puede dejar pruebas sin recoger. Comparar la colección antes y después. La ejecución con modelos reales depende de recursos locales y se registra por separado.

Los documentos de [arquitectura](architecture.md), [streaming](streaming.md) y [portabilidad](portabilidad.md) describen las restricciones actuales. El [diseño de historial](design/persistencia-historial-feedback.md) recoge decisiones y propuestas relacionadas. Actualizar esos enlaces y documentos cuando cambien las rutas efectivas.

### Secuencia propuesta y criterios de parada

Estimación orientativa para una persona con el entorno ya preparado: 5 a 9 días de trabajo, más revisión. Es una hipótesis, no una medición. Cada paso termina en un commit revisable y puede dividirse si no cabe en medio día. Antes de empezar se registra el resultado base de `mise run check` y `CI=1 pnpm --filter web e2e`, el SHA y los fallos preexistentes. No se ejecuta `mise run setup` sin autorización porque instala dependencias.

En **cada paso**, ejecutar `mise run check` y `CI=1 pnpm --filter web e2e`, además de las pruebas focalizadas indicadas. `mise run check` exporta OpenAPI, genera el cliente y ejecuta `git diff --exit-code -- services/ai/openapi.json apps/web/src/lib/api/schema.d.ts`. Ambos diffs deben quedar vacíos frente al commit anterior y al contrato base `56b1967`; revisar también `git diff 56b1967 -- services/ai/openapi.json apps/web/src/lib/api/schema.d.ts`. Comprobar enlaces internos de todos los Markdown versionados y actualizar las rutas documentadas en el mismo paso. Registrar comandos y resultados. Si faltan herramientas, el entorno falla o hay diferencias, parar sin declarar el paso verde. No aceptar una regeneración del contrato como solución a una diferencia de comportamiento.

1. **Línea base y controles** (0,5–1 día). Capturar resultados y añadir el test de límites con ejemplos positivos y negativos. Comprobar que detecta una infracción deliberada y retirarla. No activar todavía reglas que el código existente incumple.
2. **Composición y transporte** (1–2 días). Separar `bootstrap`, esquemas, rutas y SSE en incrementos; eliminar imports de historial hacia `api.py`. Ejecutar tests de API, streaming e historial en cada incremento. Mantener el punto de entrada de Uvicorn y el exportador funcionales.
3. **Puertos y persistencia** (1–2 días). Extraer protocolos de modelos, OCR, índice e historial; inyectar implementaciones y trasladar almacenamiento. Ejecutar tests de adaptadores, store, historial y feedback. Activar los límites ya alcanzados.
4. **Casos de uso y dominio** (1–2 días). Extraer ingesta, preguntas, facturas y reglas puras por flujo. Ejecutar tests de ingesta, concurrencia PDF, consultas y batería de facturas. Separar E/S antes de aplicar la regla de dominio.
5. **Web** (1–2 días). Mover una feature por commit, actualizar imports y activar restricciones ESLint. Ejecutar lint, tipos y e2e de la feature, además de la comprobación común.
6. **Tests, scripts y documentación** (0,5–1 día). Clasificar tests por alcance sin perder recolección; comparar la lista de tests antes y después. Actualizar referencias de scripts, arquitectura y estructura. Ejecutar la comprobación común y, si existen recursos locales autorizados, documentar aparte el resultado live.

Parar ante una regresión, un cambio de OpenAPI o tipos generados, un enlace roto, una dependencia circular o una regla que exija una excepción permanente. Corregir en el paso actual o volver al último commit verde. Si la separación exige cambiar comportamiento, esquema de datos, contrato HTTP, configuración pública o alcance, detenerse y pedir una decisión. La aprobación de esta propuesta no autoriza instalaciones ni cambios fuera de su alcance.

Antes de la entrega de fase 1 no se moverán ni renombrarán archivos de código, ni se modificarán tests, scripts, configuración, contratos, dependencias o workflows. Tampoco se hará push ni se tocarán otras ramas. La ejecución de los pasos queda pendiente de revisión de Miguel.
