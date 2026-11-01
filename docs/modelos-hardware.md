# Modelos y hardware

## Hardware real

Configuración medida el 1 de noviembre de 2026:

- macOS 26.6.2 (25G83).
- Apple M4, 10 núcleos de CPU y 10 de GPU.
- 16 GiB de memoria unificada.

En Apple Silicon CPU y GPU comparten memoria. Por eso no se presenta una cifra de «VRAM libre» separada: sería ficticia. Las medidas disponibles son RSS por proceso y memoria física total.

```sh
sw_vers
sysctl -n machdep.cpu.brand_string hw.physicalcpu hw.logicalcpu hw.memsize
system_profiler SPDisplaysDataType
```

## Selección final

| Función | Modelo y cuantización | Disco | Configuración | Por qué encaja en 16 GiB |
|---|---|---:|---|---|
| Respuesta y planificación | Qwen3.5-4B Q4_K_M | 2,553 GiB | contexto 8192, 2 slots, temperatura 0, `reasoning-budget 0` | Es el mayor consumidor. Q4_K_M deja margen para tres servidores auxiliares, web, API e índice y ofrece latencia interactiva. |
| Embeddings | bge-m3 Q8_0 | 0,591 GiB | 1024 dimensiones | Multilingüe y adecuado para español técnico. Su tamaño permite Q8_0 sin comprometer el presupuesto global. |
| Reranking | bge-reranker-v2-m3 Q8_0 | 0,592 GiB | endpoint local de reranking | Reduce candidatos irrelevantes antes de generar. Q8_0 cabe junto al embedding y evita delegar selección al LLM. |
| OCR | GLM-OCR Q8_0 | 0,885 GiB | contexto 8192, flash attention, máximo 1600 tokens de imagen | OCR local especializado y compatible con llama.cpp; evita API o runtime adicional. |
| Proyector OCR | mmproj GLM-OCR Q8_0 | 0,451 GiB | cargado con GLM-OCR | Necesario para la entrada visual; forma una sola decisión con el OCR. |

Los cinco archivos suman 5,072 GiB en disco. Eso no equivale a memoria de ejecución: también cuentan contexto, cachés, páginas compartidas, SQLite, Node y el sistema operativo. Los archivos, versiones y SHA256 están fijados en `scripts/assets.json`.

## Alternativas consideradas

| Alternativa | Decisión | Motivo vinculado al hardware y al riesgo |
|---|---|---|
| Qwen3.5 9B Q4_K_M | No se incluye en la entrega | En tres preguntas sintéticas no aportó una mejora observable y fue más lento. Su RSS varió entre ejecuciones y reduce el margen de una máquina de 16 GiB mientras conviven OCR, embeddings y reranker. Se reevaluaría con un gold independiente, no por tamaño nominal. |
| Cuantización menor del LLM | Descartada para esta entrega | Ahorraría memoria, pero la prioridad es fundamentación y no hay una comparación que demuestre que conserva calidad. Q4_K_M ya cabe. |
| Embeddings o reranker más cuantizados | Descartados | Cada uno ronda 0,6 GiB; el ahorro sería pequeño frente al riesgo de degradar recuperación. |
| Eliminar el reranker | Descartado | Ahorraría un proceso, pero trasladaría más fragmentos o candidatos peores al LLM. La precisión de recuperación pesa más que ese ahorro en la máquina medida. |
| Ollama para OCR | Alternativa operativa, no valor por defecto | Funcionó con GLM-OCR, pero añade otro runtime. llama.cpp ya se empaqueta, se verifica por SHA256 y sirve los cuatro roles. |
| APIs cloud | Incompatible | Viola la restricción de privacidad y procesamiento local, con independencia de su calidad. |

La comparación 4B/9B es exploratoria: tres preguntas no miden calidad general. La decisión final se apoya también en el presupuesto simultáneo y en minimizar piezas operativas, no en declarar ganador al 4B.

## Memoria observada

Instantáneas RSS con los cuatro servidores cargados y una inferencia sintética. Se usó llama-server 0.8.0, compilación 11960; el ZIP fija b12020, por lo que estas cifras son orientativas y no una medición exacta del paquete final.

| Proceso | Tras cargar | Tras inferencia del LLM |
|---|---:|---:|
| LLM | 2.961 MiB | 3.043 MiB |
| Embeddings | 325 MiB | 325 MiB |
| Reranker | 620 MiB | 617 MiB |
| OCR | 1.791 MiB | 1.791 MiB |

Son instantáneas, no picos. RSS puede contar páginas compartidas y no se suma como si fueran reservas independientes. No se ejecutó OCR simultáneo en esa muestra. La conclusión defendible es más estrecha: los cuatro modelos cargaron y operaron juntos en el M4 de 16 GiB sin agotar memoria durante los recorridos publicados.

## Latencia en el mismo equipo

Diez peticiones válidas por operación, primero en serie y después de dos en dos:

| Operación | Serie p50 / p95 | Concurrencia 2 p50 / p95 |
|---|---:|---:|
| Consulta documental | 3,115 / 3,922 s | 4,775 / 6,599 s |
| Consulta de factura | 1,747 / 3,256 s | 3,352 / 6,221 s |
| Aclaración | 1,833 / 1,969 s | 3,122 / 3,187 s |
| Rechazo | 2,126 / 3,606 s | 3,315 / 6,389 s |
| Ingesta PDF sintético | 0,054 / 0,246 s | 0,068 / 0,084 s |
| Ingesta de factura sintética | 15,057 / 16,922 s | 29,131 / 31,338 s |

El p95 usa interpolación inclusiva sobre diez muestras, por lo que es inestable. Los bloques no tuvieron calentamiento controlado ni máquina dedicada. Sirven para identificar el cuello de botella —OCR— y confirmar una experiencia interactiva local; no son un SLA.

La corrida reproducible `mise run evidence --live` publica además tiempos por fichero y pregunta en `evidence/live/results.md`.

## Criterio para cambiar un modelo

Un cambio solo es aceptable si se repite el mismo conjunto independiente y mejora el compromiso relevante:

1. ninguna respuesta sin respaldo;
2. tasa de respuesta correcta y de rechazo correcto;
3. recall de recuperación y precisión de citas;
4. p50/p95 y pico de memoria con los cuatro roles cargados;
5. extracción por campo y puertas aritméticas para facturas.

Hasta disponer de ese conjunto, subir parámetros o cambiar cuantización sería una apuesta, no una mejora acreditada.
