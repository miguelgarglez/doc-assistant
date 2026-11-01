# Escalado y despliegue (descrito, no implementado)

La propuesta ampliada de aislamiento, permisos, colas, operación y fases está en [arquitectura multiusuario](design/arquitectura-multiusuario.md). Cuando este resumen y esa propuesta difieran, prevalece la propuesta ampliada.

## Hoy
Un portátil (M4, 16 GB): 5 procesos locales, SQLite en un fichero. Pensado para un usuario.

## Qué escala y cómo
| Pieza | Límite actual | Siguiente paso |
|---|---|---|
| LLM | 2 peticiones paralelas (`-np 2`), ~27 tok/s | Servidor GPU con vLLM/llama.cpp y varias réplicas detrás de una cola; modelo mayor (9B+) solo cambiando config |
| Embeddings / reranker | CPU/Metal compartido con el LLM | Servicio propio, por lotes; reindexado offline |
| Índice | SQLite + sqlite-vec (miles de fragmentos) | Postgres + pgvector, o un motor vectorial dedicado, cuando haya >1 M fragmentos o varios escritores |
| Facturas | Tabla SQL local | Postgres; la ingesta pasa a una cola de trabajos (OCR es lo más lento) |
| Web | `next start` local | Contenedor sin estado detrás de un balanceador; escala por tráfico, separada de la IA |

## Despliegue propuesto
- Web y servicio de IA como contenedores separados (el contrato OpenAPI ya los desacopla). La IA en nodos con GPU; la web en nodos baratos.
- La capa de servidor de Next (hoy solo proxy) es donde irían autenticación, multiusuario, historial y límites de uso. No se construye ahora a propósito.
- Observabilidad: tiempos por etapa (ya se devuelven en ingesta), trazas por petición y métricas de rechazo.
- Datos sensibles (facturas): cifrado en reposo y despliegue on-premise si el cliente lo exige; los modelos ya son locales.

## Riesgos al escalar
- Más usuarios pueden saturar el LLM u otra etapa. Medir cada etapa antes de dimensionar colas y réplicas.
- Un modelo mayor cambia la tasa de rechazos y aciertos: hay que reevaluar con el mismo conjunto antes de cambiarlo.

## Herramienta para toda la ingeniería

**Leyenda.** **[preparado]**: la costura ya existe en el código. **[no implementado]**: solo está diseñado.

- **Multiusuario y autenticación** [no implementado]: SSO (OIDC con el IdP corporativo) en la capa servidor de Next, que hoy solo hace de proxy y es el único punto de entrada [preparado]. La IA no se expone; recibe la identidad en una cabecera firmada.
- **Permisos por colección y colecciones por equipo** [no implementado]: una colección es un conjunto de documentos con su ACL (equipo, planta). Cada búsqueda filtra por las colecciones del usuario *antes* de recuperar, para que el LLM nunca vea un fragmento que el usuario no puede leer. Hoy hay un índice único.
- **Ingestión incremental y versionado** [parcial]:
  - Hoy: `doc_id` opaco, reingesta idempotente por hash y `replace_document` transaccional [preparado].
  - Falta: guardar versiones (`doc_id` + `version`), que las citas apunten a la versión vigente, histórico consultable, y vigilar carpetas o un DMS (SharePoint) con una cola.
- **Concurrencia y cola de inferencia** [no implementado]: hoy el LLM atiende 2 peticiones en paralelo (`-np 2`). Siguiente paso: una cola (Redis/NATS) con límites por usuario delante de N réplicas de llama-server o vLLM. Ingesta y OCR van a workers aparte para no competir con las preguntas.
- **Observabilidad** [parcial]:
  - Hoy: tiempos por etapa en la ingesta y errores tipados `{code, message}` [preparado].
  - Falta: OpenTelemetry por petición (recuperación, reranker, LLM y verificador) y métricas de tasa de rechazo, latencia p95 y uso por colección. Sin registrar el contenido de documentos sensibles.
- **Evaluación continua** [no implementado]: el gold aprobado se ejecuta en CI y en cada cambio de modelo o de config. Si sube la tasa de respuestas sin evidencia, el cambio se bloquea. `mise run evidence --live` es el embrión [preparado].
- **Almacenamiento** [preparado a medias]:
  - Hoy: SQLite + sqlite-vec detrás de `ChunkStore`, con el esquema versionado (`PRAGMA user_version`).
  - Para cambiar: pgvector o Qdrant, sujetos a pruebas de recall filtrado, aislamiento, latencia y coste. Hace falta extraer de `ChunkStore` una interfaz explícita; ver "Costuras" más abajo.
- **Despliegue en servidor GPU** [no implementado]: los modelos y la config ya son intercambiables por `config.yaml` [preparado]. El tamaño de GPU, la cantidad de réplicas y el batching requieren pruebas con los modelos y la carga previstos. Embeddings y reranker van en una GPU pequeña o en CPU. On-premise por planta, o centralizado con réplicas por región si la latencia lo exige.
- **Coste** [no implementado]: el coste dominante es la GPU del LLM. Por orden de palanca: cachear preguntas repetidas por colección, usar el modelo pequeño para el enrutado o plan y el grande solo para responder, y apagar réplicas fuera de horario. La operación local también tiene costes de hardware, energía y personal.

### Costuras baratas (propuestas; no aplicadas aún)
1. **Factoría `open_store(cfg)`**: hoy `ChunkStore(...)` se construye en 4 sitios con `dim` por defecto distinto (`dim` frente a `dim or 8`). Unificarlo en un punto es mecánico y deja un único sitio para cambiar a pgvector o Qdrant. No se ha aplicado porque unificar ese `dim` cambia el comportamiento y hay que probarlo aparte.
2. **`collection_id` opcional en `/ask` y `/documents`** (por defecto `"default"`): exige una columna nueva, subir `SCHEMA_VERSION` (el índice se reconstruye solo) y regenerar el contrato y la UI. Es barato, pero solo merece la pena con permisos detrás. Si no, es un filtro sin seguridad.
3. **Identidad del usuario en el proxy**: el BFF reenviaría `x-user` cuando exista autenticación. Hoy no hay nada que reenviar.
