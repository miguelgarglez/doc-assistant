# Huecos del enunciado y decisiones

El enunciado deja huecos a propósito. Para cada uno: qué se decidió, por qué y qué alternativa queda.

| Hueco | Decisión | Por qué | Alternativa |
|---|---|---|---|
| Idioma de preguntas y documentos | Español en la UI, los prompts y los rechazos; modelos multilingües (bge-m3) | Los usuarios son ingenieros hispanohablantes | Detectar el idioma y responder en el de la pregunta |
| Qué cuenta como "fuente exacta" | Documento + sección + página + fragmento literal; la cita debe aparecer tal cual en el fragmento | Es verificable por código, sin depender del LLM | Coordenadas en la página (bbox) para resaltar sobre la imagen |
| Qué hacer si la evidencia es parcial | Rechazar ("no dispongo") antes que responder a medias | Inventar es un fallo grave; rechazar de más es un fallo leve | Respuesta parcial marcada como tal |
| Campos de factura | Número, fecha, emisor, cliente, NIF, base, IVA, IRPF y total; los ausentes van como `null` | Son los que aparecen en facturas españolas y permiten las puertas aritméticas | Esquema configurable por cliente |
| Factura que no cuadra | Se guarda con estado "revisar" y su motivo; las respuestas lo avisan | Mejor un dato marcado que uno descartado o en silencio | Bloquear la consulta hasta que alguien la revise |
| Preguntas agregadas sobre facturas ("suma de todas") | Contar y sumar con SQL generado por código sobre columnas tipadas; el LLM solo elige la intención (ADR-012) | Las cifras salen de la base, no del modelo | Agrupar por mes o por persona (no implementado) |
| Formato de fecha | El texto original se conserva; una columna derivada guarda la fecha ISO cuando una regla la reconoce (día/mes/año, ISO, nombre del mes). Si no la reconoce, queda nula y la factura no entra en filtros de fecha | Normalizar sin regla podía inventar | Pedir la fecha al revisar la factura |
| Pregunta sobre facturas con persona o número ambiguo | Se pregunta «¿De qué factura?» con hasta 5 candidatas como botones; cada una reenvía la pregunta con su número (ADR-013). Nunca se elige una al azar | Elegir mal es una respuesta falsa, y un rechazo decía lo contrario de lo que pasaba | Recordar la elección en la conversación; candidatas de persona para listas, conteos y sumas |
| Mes sin año ("facturas de marzo") | Cualquier año; el año solo se toma de la pregunta, nunca del modelo | El modelo inventaba el año | Usar el año en curso |
| Cómo acreditar "cero alucinaciones" | No se afirma ninguna cifra hasta tener un gold aprobado; hay pruebas de humo y evaluaciones sintéticas con límites documentados | Una cifra sobre un borrador no acredita nada | Gold aprobado + métricas reproducibles en `mise run evidence` |
| OCR | GLM-OCR GGUF Q8_0 en llama-server :8084 (en el ZIP) | Medido frente a Ollama glm-ocr con 6 facturas sintéticas y el LLM cargado: 72/72 campos ambos, ~22 s/factura frente a 27–36 s, ~2,3–2,7 GB de RAM pico | Ollama queda como alternativa (`DOC_ASSISTANT_OCR_RUNTIME=ollama`) |
| Hardware objetivo | El portátil disponible (M4, 16 GB); modelos de 4B cuantizados | El enunciado no da hardware | Un servidor GPU (ver `scaling-deployment.md`) |
| Sistema operativo del evaluador | mise + scripts Python, sin shell ni Docker | Es lo que funciona igual en macOS, Linux y Windows | Docker o WSL2 como plan B |
| Usuarios y permisos | No hay: es una herramienta de un solo usuario y local | Está fuera del núcleo pedido | Autenticación en la capa servidor de Next (ver `scaling-deployment.md`) |
| Formato de entrega de la evidencia | Va dentro del ZIP ya generada, y se puede regenerar | El evaluador puede verla sin ejecutar nada | Que solo se pueda regenerar |
| Preguntas panorámicas ("¿qué sabes hacer?", "¿de qué trata X?") | Se responden sin LLM con metadatos reales del índice (documentos, títulos, apartados citados literalmente y la primera frase del alcance) | Mantiene cero invenciones y deja de rechazar lo que sí se sabe (ADR-009) | Resumen por documento generado en la ingesta y verificado frase a frase |
| Respuesta en tiempo real frente a verificación | Texto provisional en streaming, verificado al final; si falla, se retira y se sustituye por el rechazo | El texto puede verse antes del resultado final; `done` prevalece y no se acepta una respuesta sin verificar (ADR-009) | Retener el texto hasta verificarlo |

## Decisiones incorporadas hasta v0.15.2

| Hueco | Decisión actual | Límite pendiente |
|---|---|---|
| Presentar cifras y listas sin perder evidencia | Bloques `key_data` y `table` construidos en el servicio, con citas y `blocks_version: 1` (ADR-014) | Markdown completo ante versión desconocida o bloques inválidos; sin posiciones OCR |
| Saturación de consultas | Dos consultas activas y cuatro en espera por proceso, hasta 60 segundos; `queue_full` o `queue_timeout` para reintentar | Sin cola durable ni límite de ingestas; falta medir carga sostenida y equidad |
| Diagnóstico de la última consulta | Sistema reconstruye la traza desde SSE y conserva códigos de fallo temprano | Sin historial persistente ni opción de trazas internas en la configuración del servicio |
| Etiquetas de importes con dos puntos | El extractor admite el separador y conserva la evidencia literal | La repetición sintética obtuvo 11 coincidencias de 12 con un oráculo limitado; no acredita precisión general |

Fuentes: [arquitectura](architecture.md), [CHANGELOG](CHANGELOG.md), [evaluación sintética](../evidence/evaluacion-sintetica/README.md). Las decisiones abiertas están en [decisiones pendientes](decisiones-pendientes.md).
