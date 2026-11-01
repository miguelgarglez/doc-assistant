# Persistencia del historial de peticiones y feedback con traza

Estado: implementación parcial interna, sin persistencia conectada ni interfaz de historial. La propuesta multiusuario y sus límites de seguridad están en [arquitectura multiusuario](arquitectura-multiusuario.md). ADR-014 ya corresponde a respuestas enriquecidas; una decisión futura sobre historial necesita otro identificador.

Dos peticiones del backlog dependen de lo mismo: guardar cada petición con su traza.
1. Un historial de consultas en Sistema, no solo la última.
2. Un botón de feedback («esta respuesta es incorrecta») que adjunte la traza completa para estudiarla después.

## 1. Qué hay hoy

| Dato | Dónde vive hoy | Límite |
|---|---|---|
| Preguntas anteriores | `sessionStorage` del navegador (`use-question-history.ts`), 40 como máximo | Solo el texto de la pregunta, por pestaña. Se pierde al cerrar. |
| Traza de la última consulta | Memoria del cliente (`lastTrace` en `chat-provider.tsx`), reconstruida de los eventos `step` | Solo la última. Sin fragmentos ni puntuaciones. |
| Conversación | Estado de `useChat` | Se pierde al recargar. |
| Petición en el servicio | `x-request-id` en la respuesta y `request_id` en `done` | El servicio no guarda la petición. |
| Tiempos | `done.timings` (por etapa y total) | Solo llegan al cliente. |
| Etapa `rerank` | `data.top`: documento y sección de cada fragmento seleccionado | No incluye `chunk_id`, puntuación vectorial, BM25 ni del reranker. |
| Versiones | `config.yaml` guarda el nombre de cada modelo; `PRAGMA user_version` guarda el esquema del índice | Sin hash del modelo cargado, sin versión del prompt ni revisión del índice. |
| Usuarios | No existen (`open-gaps.md`, `scaling-deployment.md`) | El BFF de Next es hoy solo un proxy. |

Conclusión: una traza útil para diagnosticar exige capturar más datos en el servicio. El cliente no tiene las puntuaciones y no se le debe confiar la traza.

## Avance de la traza interna

El servicio dispone de un colector opcional en memoria y de un almacén SQLite aislado. Ningún endpoint activa el colector ni escribe en el almacén. El colector registra el identificador de petición en el stream, el estado y los errores de cola, los pasos, las puntuaciones y el orden de candidatos, el resultado y los detalles de verificación. En consultas de facturas también recoge el plan, el SQL parametrizado y las filas seleccionadas.

El almacén limita el listado, la lectura de una petición y la copia de su traza a la conversación indicada por el llamador. Esto evita asociar por error una petición a otra conversación, pero el identificador de conversación no autentica al llamador ni garantiza aislamiento entre usuarios. La autorización debe comprobarse antes de exponer estas operaciones.

La huella `chunk_index_sha256` cubre las filas de fragmentos documentales en la misma transacción de lectura que la búsqueda. No cubre vectores, facturas ni archivos de origen. Calcularla recorre todos los fragmentos: falta medir su coste con índices representativos antes de conectar la persistencia. Los nombres de modelos son los de configuración, no una prueba de qué archivos están cargados. La traza todavía no contiene todas las versiones ni la selección entre aclaraciones.

Una prueba exploratoria ejecutó el mismo recorrido y serialización de la huella sobre SQLite en memoria, con fragmentos sintéticos de texto repetido. Tras una pasada de calentamiento, diez mediciones dieron p50/p95 de 5,23/5,40 ms para 1.000 filas, 55,40/56,64 ms para 10.000 y 561,73/565,47 ms para 100.000. El coste creció aproximadamente con el número de filas en esta muestra. No incluye lectura desde disco, búsquedas, concurrencia ni una petición completa; tampoco representa la distribución de textos de un índice real. El script y las muestras están en `_agents/night2/`. Antes de activar la traza hay que medir índices representativos y decidir cómo evitar un recorrido completo por petición si el coste resulta excesivo.

El almacén y el colector son piezas aisladas. Antes de activar la persistencia faltan la política de privacidad y retención, el tratamiento de errores y desconexiones de extremo a extremo, los endpoints, la interfaz y la medición del coste sobre una petición completa.

## 2. Qué debe guardar una petición

Todo se escribe una sola vez, al terminar la petición, con el estado final de `done`, o de `error` si falla.

- Identidad: `request_id`, `conversation_id`, `user_id` (nulo o `local` sin autenticación), instante de inicio y de fin.
- Entrada: pregunta literal y, si la hubo, la pregunta desambiguada que viene de una aclaración (ADR-013).
- Resultado: `ok`, `reason`, tipo de resultado (respuesta, rechazo, aclaración, error), texto final y `inline`.
- Pasos: cada evento `step` con su `id`, `data` y `elapsed_s`.
- Recuperación: por cada fragmento candidato, `chunk_id`, posición, puntuación vectorial, BM25, puntuación del reranker y si pasó al contexto. En facturas: el plan validado, el SQL parametrizado y las filas seleccionadas.
- Verificación: cada cita con su `chunk_id`, el `quote` y si pasó; segmentos inline.
- Aclaración: candidatas ofrecidas y, cuando llegue la pregunta siguiente, cuál se eligió.
- Tiempos: `timings` completo.
- Versiones en el momento de la petición: LLM, embeddings, reranker y OCR (nombre y SHA256 del fichero, que `assets.json` ya fija), versión del prompt, `SCHEMA_VERSION` del índice, revisión del índice (hash de los `doc_id` y sus hashes de contenido), versión de la aplicación (tag) y hash de `config.yaml`.

Formato: un JSON de traza con `trace_schema_version`, más columnas indexables (`user_id`, `created_at`, `ok`, `reason`, `conversation_id`). El JSON permite cambiar la traza sin migrar tablas. Las columnas permiten listar y filtrar sin abrirlo.

## 3. Cambios de contrato (aditivos)

- `request_id`: cabecera `x-request-id` en `/ask`, `/ask/stream` y en `done`. Un cliente anterior lo ignora.
- Las etapas `retrieve` y `rerank` añaden `chunk_id` y las puntuaciones, solo en la traza guardada. A la web le sigue llegando lo que le llega hoy, para no ensanchar el stream ni mostrar puntuaciones sin diseño.
- Endpoints nuevos: `GET /history?conversation_id=&cursor=`, `GET /history/{request_id}`, `POST /feedback`.
- Para un prototipo local se había propuesto una cabecera `x-user-id`. Una instalación multiusuario necesita identidad verificada y autenticación entre servicios; una cabecera arbitraria y una red privada no bastan. Ver la propuesta multiusuario.

## 4. Opciones de persistencia

| | A. SQLite propio en el servicio | B. Base de datos en el BFF de Next | C. Postgres compartido, el servicio es propietario | D. Solo logs y OpenTelemetry |
|---|---|---|---|---|
| Quién tiene los datos de recuperación | El servicio, donde se producen | El BFF solo ve lo que le llega por SSE | El servicio | El servicio |
| Puntuaciones y versiones | Completas | Faltan, salvo que el servicio las envíe en cada respuesta | Completas | Completas, pero como texto no consultable |
| Consulta («fallos de ayer, por motivo») | SQL | SQL | SQL | Hay que montar un colector |
| Multiusuario real | Un escritor por proceso. Vale hasta pocas decenas de usuarios; después, cuello | Sí | Sí | No es un historial |
| Operación hoy | Cero: un fichero junto al índice | Hay que meter una base de datos en el BFF | Hay que desplegar Postgres | Hay que desplegar un colector |
| Costura hacia escala | Interfaz `HistoryStore` con otra implementación | Rehacer | Ya está | No aplica |
| Riesgo | Escalado horizontal del servicio (varios procesos, cada uno con su fichero) | Dos fuentes de verdad para una traza | Más piezas para una herramienta local | No cumple el feedback con traza adjunta |

## 5. Recomendación

Por fases, con una interfaz que permita el salto:

1. Opción A ahora. El servicio guarda las peticiones en un fichero SQLite distinto del índice (`history.db`, WAL) detrás de una interfaz `HistoryStore` (`record`, `get`, `list`, `add_feedback`). El fichero nuevo aísla el historial de la reindexación: si `ensure_schema` aparta el índice por un cambio de esquema, el historial sobrevive.
2. Opción C cuando haya autenticación real y más de un proceso del servicio. Es otra implementación de `HistoryStore` y una migración de datos de un solo paso (volcado de las filas y del JSON de traza). No hay que cambiar el contrato ni la web.

Se descarta B porque duplica la fuente de verdad y no tiene las puntuaciones. Se descarta D como sustituto, porque no deja ningún historial consultable ni feedback vinculado a una traza; sí conviene como complemento cuando exista OpenTelemetry (`scaling-deployment.md`).

Conversaciones: se persiste `conversation_id` como agrupación de peticiones, no el hilo renderizado. La web reconstruye el hilo desde las peticiones (`GET /history`), que ya llevan pregunta, respuesta y citas.

## 6. Esquema propuesto

```sql
CREATE TABLE requests (
  request_id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  user_id TEXT NOT NULL DEFAULT 'local',
  created_at TEXT NOT NULL,          -- ISO 8601 UTC
  question TEXT NOT NULL,
  kind TEXT NOT NULL,                -- answer | refusal | clarification | error
  ok INTEGER NOT NULL,
  reason TEXT NOT NULL,
  total_s REAL,
  trace_schema_version INTEGER NOT NULL,
  trace_json TEXT NOT NULL
);
CREATE INDEX requests_user_time ON requests(user_id, created_at DESC);
CREATE INDEX requests_conversation ON requests(conversation_id, created_at);

CREATE TABLE feedback (
  feedback_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,                -- incorrecta | cita_equivocada | falta_informacion | otro
  comment TEXT,
  status TEXT NOT NULL DEFAULT 'nuevo',
  trace_json TEXT NOT NULL           -- copia de la traza en ese momento
);
```

La traza se copia en `feedback`. Si una política de retención borra la petición, el feedback conserva lo necesario para estudiar el caso.

## 7. Botón de feedback

- Dónde: en la barra de acciones del mensaje del asistente, junto a copiar y regenerar. Un solo botón abre un menú con las cuatro razones y un comentario opcional. No se adjunta nada del navegador salvo el `request_id`, el motivo y el comentario.
- Qué se envía: `POST /feedback {request_id, kind, comment}`. El servidor busca la petición y copia la traza completa. El cliente no la sube: así no se puede falsear, no pesa en la red y no depende de lo que el cliente haya conservado.
- Confirmación: aviso de Sonner con el identificador del feedback. Sin animación de entrada propia.
- Estado: `nuevo`, `revisado`, `convertido a caso` y `descartado`. El comando interno `python -m doc_assistant.feedback_export RUTA_DB --conversation-id ID` escribe en stdout los borradores revisados con respuesta esperada. La salida incluye la traza y puede contener datos confidenciales; protege cualquier archivo al que la redirijas. La base debe existir y el comando puede aplicar migraciones del almacén. De ahí salen los casos del gold, con el mismo formato que usará la evaluación.
- Una petición con `error` o rechazo también admite feedback (por ejemplo, «debería haber respondido»).

## 8. Privacidad y retención

La traza contiene preguntas y texto literal de documentos y facturas, que pueden ser confidenciales.

- Por defecto se guarda el texto de los fragmentos, porque sin él no se puede reproducir un fallo si el documento cambia. Un ajuste `history.store_fragment_text: false` guarda solo `chunk_id`, hash y posición.
- Retención configurable (`history.retention_days`; propuesta de partida: 90). El feedback se conserva hasta que se descarta.
- Cada usuario ve solo sus peticiones. Un rol revisor ve el feedback, con una vista aparte.
- Borrado por usuario y por conversación. Se mueve a `_trash/` en local, como el resto de operaciones destructivas del repo; en producción, un borrado real auditado.
- `history.db` queda fuera del ZIP de entrega y de `evidence/`.
- Con el servicio local y un usuario no hay datos de terceros. La política completa se decide cuando exista multiusuario.

## 9. Migración y despliegue por fases

| Fase | Contenido | Reversible |
|---|---|---|
| 0 | `request_id` en cabecera y en `done`; el servicio construye la traza completa en memoria, con puntuaciones y versiones. Pruebas de la traza. Nada se persiste. | Sí: campo aditivo. |
| 1 | `HistoryStore` con SQLite (`history.db`), `GET /history`, historial en Sistema. | Sí: borrar el fichero. El índice no se toca. |
| 2 | `POST /feedback`, botón, exportación JSONL. | Sí. |
| 3 | Identidad en el BFF (`x-user-id`), filtros por usuario, retención y borrado. | Sí, con `user_id='local'` como valor por defecto. |
| 4 | `HistoryStore` sobre Postgres cuando haya varios procesos. Volcado único de las tablas. | Se conserva el fichero antiguo. |

El historial de preguntas de `sessionStorage` no se migra. Queda como recuerdo con ↑ del compositor y la ayuda de teclado, y desaparece cuando exista `GET /history`.

## 10. Pruebas propuestas

- Servicio: una petición de cada tipo (respuesta, rechazo, aclaración, error) guarda una traza con todos los campos de la sección 2; una petición interrumpida deja el registro con `error`; `HistoryStore` pasa la misma batería con SQLite y, más adelante, con Postgres.
- Aislamiento: un usuario no lista ni abre peticiones de otro (incluido el `GET /history/{id}` directo).
- Feedback: la traza guardada es la del servidor y no la que mande el cliente; sobrevive a borrar la petición.
- Contrato: `request_id` presente en `done` y en la cabecera; OpenAPI sin deriva.
- Web: el menú de feedback se maneja con teclado y pasa axe en cuatro temas y modos.
- Rendimiento: medir el coste de escribir la traza sobre la latencia de una petición. No hay medida todavía. Hay que tomarla antes de aceptar la fase 1.

Una medición exploratoria local de `HistoryStore.record` usó 100 escrituras consecutivas de una traza sintética con 40 candidatos y sin texto de fragmentos. La traza JSON ocupó 8.524 bytes; cada operación abrió la conexión, serializó y confirmó una fila. La mediana fue 0,54 ms y el p95 interpolado 0,73 ms, con un rango de 0,40 a 1,08 ms. Las 100 filas se leyeron después. Es una sola serie, sin carga concurrente ni perfilado, y no mide el coste en una petición completa. No permite aceptar la fase 1 ni estimar el tamaño con fragmentos literales. El script y las muestras están en `_agents/night2/`.

## 11. Decisiones abiertas

1. ¿Se guarda el texto de los fragmentos por defecto? La propuesta dice que sí, por reproducibilidad.
2. ¿Hay un rol revisor distinto de los usuarios, o lo ve todo el administrador?
3. ¿Qué retención se acepta para preguntas y fragmentos?
4. ¿La conversación persiste entre dispositivos (necesita identidad) o solo en el equipo?
5. ¿El tamaño medio de una traza con 40 candidatas es aceptable? Sin medida: se mide en la fase 0.

## 12. Qué no cubre

- No hay autenticación ni permisos por colección (ver `scaling-deployment.md`).
- No se propone telemetría de uso ni métricas agregadas; eso es OpenTelemetry.
- No se decide el formato del gold; solo que el feedback exportado pueda alimentarlo.
