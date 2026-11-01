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
