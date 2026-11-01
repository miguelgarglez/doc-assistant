# Modelos y hardware

La configuración actual se ha probado en el Mac descrito en [README](../README.md#probado-en). Los nombres, tamaños y hashes de los archivos proceden de `scripts/assets.json`. Los tamaños de esta tabla son los archivos en disco, no el consumo de memoria en ejecución.

| Función | Archivo | Cuantización | Tamaño en disco |
|---|---|---|---:|
| Respuesta y planificación | Qwen3.5-4B-Q4_K_M.gguf | Q4_K_M | 2,553 GiB |
| Embeddings | bge-m3-Q8_0.gguf | Q8_0 | 0,591 GiB |
| Reordenación | bge-reranker-v2-m3-Q8_0.gguf | Q8_0 | 0,592 GiB |
| OCR | GLM-OCR-Q8_0.gguf | Q8_0 | 0,885 GiB |
| Proyector visual para OCR | mmproj-GLM-OCR-Q8_0.gguf | Q8_0 | 0,451 GiB |

Los cinco archivos suman aproximadamente 5,072 GiB. La memoria unificada disponible es de 16 GiB, pero esa resta no predice la memoria libre durante la ejecución. El sistema operativo, los procesos, el contexto y las estructuras de inferencia también ocupan memoria. Falta medir el pico de memoria con los cuatro servidores activos y durante OCR y consulta.

La división por función permite cambiar cada modelo sin sustituir toda la aplicación. `config/config.yaml` define los servicios y `scripts/assets.json` fija sus archivos. Los resultados anteriores documentan pruebas de humo y baterías sintéticas, no una comparación controlada entre modelos ni una evaluación gold aprobada.

## Alternativas que faltan por medir

- Un modelo de lenguaje mayor puede mejorar o empeorar las respuestas y necesita más recursos. Comparar calidad, latencia y memoria con el mismo conjunto aprobado antes de cambiarlo.
- Otra cuantización puede cambiar memoria y calidad. Medir ambas en el mismo hardware antes de elegirla.
- Ollama con GLM-OCR es una alternativa de runtime ya documentada en el README. No hay una comparación reproducible frente a llama-server en este repositorio.
- Sustituir embeddings o reranker exige reindexar o repetir la recuperación según corresponda. Comparar recuperación y citas con un conjunto aprobado antes de cambiar esos modelos.

No se conocen comparaciones documentadas que permitan presentar estas alternativas como descartadas por resultados. C4/C5/E-C1 y E-B2 siguen abiertos hasta disponer de esa evidencia.

## Muestra de memoria residente (1 de noviembre)

En el Mac del README se arrancaron los cuatro modelos de `scripts/dev.py` por separado en los puertos 8181–8184, con los mismos argumentos del plan y `llama-server` ya instalado, versión 0.8.0 (compilación 11960). Esta compilación no es la b12020 fijada para el paquete. Tras recibir `/health` de los cuatro, se consultó `ps -o pid,pgid,rss -p PID`; luego se hizo una petición de texto sintética al LLM y se repitió la consulta. RSS se expresa aquí en MiB a partir de KiB informados por `ps`.

| Proceso | Tras cargar | Tras inferencia del LLM |
|---|---:|---:|
| LLM | 2.961 MiB | 3.043 MiB |
| Embeddings | 325 MiB | 325 MiB |
| Reranker | 620 MiB | 617 MiB |
| OCR | 1.791 MiB | 1.791 MiB |

Son dos instantáneas, no el pico de una carga completa; RSS puede incluir páginas compartidas y no permite sumar sin más ni separar memoria GPU en este Mac de memoria unificada. No hubo OCR, recuperación ni trabajo concurrente durante la consulta. La versión de llama.cpp, el contexto y la carga afectan los resultados. Por eso E-B2 sigue parcial: faltan pico de memoria y carga representativa con la compilación de entrega. Los cuatro procesos se cerraron por sus PID y sus puertos quedaron libres.

## Comparación exploratoria de dos modelos de lenguaje

Con los dos archivos Qwen3.5 Q4_K_M locales se ejecutaron tres preguntas sintéticas idénticas, secuencialmente y con temperatura 0: dos datos literales y una ausencia explícita. Ambos devolvieron los tres resultados esperados. Las respuestas fueron `4 m`, `24 V` y `No está indicado.` para ambos. El servidor fue la compilación 11960, con contexto 8192 y dos slots. Hubo otra actividad en el equipo, incluidas pruebas de navegador. Una sola ejecución por pregunta no permite comparar calidad ni rendimiento de forma fiable.

| Modelo | RSS al cargar | RSS tras las consultas | Tiempos observados |
|---|---:|---:|---|
| Qwen3.5 4B | 3.152 MiB | 3.420 MiB | 0,30 / 0,35 / 0,40 s |
| Qwen3.5 9B | 2.630 MiB | 2.902 MiB | 0,55 / 0,61 / 0,67 s |

La RSS observada del 9B fue menor en esta muestra. No es el consumo total ni demuestra que necesite menos memoria: la residencia de páginas y la memoria del dispositivo pueden variar. No se ha medido el pico. Los tiempos incluyen la petición HTTP y corresponden a salidas cortas; no son una comparación controlada ni predicen tiempos de la aplicación. El experimento no permite descartar ninguna alternativa y C4/C5/E-C1 sigue en «no».

Para repetirlo en macOS con los dos GGUF ya disponibles y `llama-server` compatible en PATH:

```sh
DOC_ASSISTANT_MODELS_DIR=/ruta/a/modelos uv run --frozen --project services/ai python evidence/modelos/comparar.py
```

Usa el puerto 8181 y cierra por PID los servidores que crea. Se puede seleccionar otro ejecutable mediante `DOC_ASSISTANT_LLAMA_SERVER`; las cifras dependen de su versión y de la carga del equipo.
