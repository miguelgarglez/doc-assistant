# Escalado y despliegue (descrito, no implementado)

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
- Más usuarios ⇒ el LLM es el cuello de botella; la cola y las réplicas lo resuelven, no la web.
- Un modelo mayor cambia la tasa de rechazos y aciertos: hay que reevaluar con el mismo conjunto antes de cambiarlo.
