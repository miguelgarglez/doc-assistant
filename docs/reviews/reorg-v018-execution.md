# Diseño de ejecución de la reorganización v0.18

Este documento conserva el diseño seguido para completar la estructura aprobada desde
`875e277`. La ejecución terminó sin cambiar el contrato ni el comportamiento. El estado
actual está en `docs/repo-structure.md`.

## Decisiones

`bootstrap.py` compone la aplicación y expone `app`. El paquete `api/` solo contiene
rutas, esquemas, errores y traducción SSE. `scripts/dev.py` y `export_openapi.py` cambian
al nuevo entrypoint en el mismo commit. Así se conserva el arranque del servicio sin que
`api` alcance `infra`, ni directa ni transitivamente.

Los casos de uso reciben puertos pequeños y valores propios de su operación. No habrá un
contenedor global de servicios ni una copia completa de `AppConfig`. Una fuente de
configuración conserva cada punto de carga actual, incluida la segunda carga de
`ask_invoices`. Una pregunta vacía o demasiado larga seguirá terminando antes de leer el
YAML.

Los clientes de modelos siguen siendo perezosos. Un `ModelProvider` inyectable los crea
solo en la rama que los usa. Los dobles salen del paquete instalable y pasan a
`services/ai/tests/`.

`InvoiceWriter.save` sigue siendo la frontera de la escritura de facturas. El mismo
objeto SQLite escribe `facturas`, los fragmentos, FTS, vectores y la página. Hace un solo
`commit`; cualquier fallo hace `rollback`; el fichero se reemplaza después. La
reorganización no introduce una unidad de trabajo ni divide ese método.

Los comandos `python -m doc_assistant.feedback_export`, `feedback_review` e
`history_clear` permanecen en la raíz porque sus rutas son interfaces documentadas. El
test final de arquitectura usa una lista cerrada de entradas raíz.

## Formas de datos

Cada flujo usa un valor estrecho:

- `AskSettings` contiene `db`, `top_k`, modos de respuesta, dimensión, nombres de
  modelos y la huella de configuración.
- `IngestSettings` contiene `db`, `data_dir` y dimensión.
- `InvoiceSettings` contiene `db`, `data_dir` y dimensión.
- `UploadLimits` contiene los límites de bytes y páginas usados por las rutas.
- `ProbeResult` contiene `id`, `status`, `latency_ms` y `detail`.

Los puertos esconden las operaciones que deben compartir una conexión:

- `RetrievalIndex.search` obtiene huella, búsquedas y fragmentos en una sesión.
- `SourceCatalog.remove` elimina el índice y la fila de factura en una transacción, y
  mueve el fichero solo después del `commit`.
- `InvoiceCatalog` abre el lector y recupera filas o imágenes.
- `PdfArchive` guarda el original; `PdfIngest` extrae texto y renderiza páginas con el
  bloqueo PDFium existente.

## Orden de implementación

Cada unidad borra el módulo raíz sustituido cuando migra su último caller. No se dejan
reexports ni excepciones temporales.

1. Corregir la propiedad de tipos entre puertos y quitar `ChunkStore.from_config`.
2. Llevar las factorías de modelos a composición y los dobles a tests.
3. Separar salud en sondas de infraestructura, coordinación de aplicación y esquemas
   HTTP.
4. Mover fuentes detrás de `SourceCatalog`.
5. Mover facturas detrás de `InvoiceCatalog` sin tocar `InvoiceWriter.save`.
6. Mover la ingesta detrás de `PdfArchive`, `PdfIngest` y el puerto de índice.
7. Mover la tubería de preguntas a `application/ask` con modelos y configuración
   perezosos.
8. Separar esquemas, streaming e historial HTTP.
9. Crear `api/`, registrar las rutas en el orden actual y mover la composición final a
   `bootstrap.py`.
10. Añadir el test AST sobre todo el paquete, sin excepciones.

Después siguen las features web, la clasificación de tests, las herramientas y la
documentación final, en el orden aprobado.

## Puertas

Cada commit ejecuta `mise run check` y `CI=1 pnpm --filter web e2e`. OpenAPI y el cliente
generado deben seguir idénticos a `56b1967`. También se comprueba que no quede ningún
caller del módulo eliminado.

Se detiene el incremento ante un cambio de contrato, un ciclo, una excepción permanente
en las reglas o una diferencia de comportamiento. El test AST se añade después de cerrar
las capas, como pidió Miguel.

## Síntesis

La base elegida conserva los puntos exactos de carga, el orden del streaming y la
inyección comprobable. Del diseño alternativo se toman los puertos pequeños y el rechazo
de una unidad de trabajo visible. Se descartan el contenedor global, el espejo completo
de configuración, los parches sobre factorías globales y cualquier test AST anticipado.
