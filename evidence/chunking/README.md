# Comparación exploratoria de troceado

Desde la raíz, con las dependencias del servicio instaladas:

```sh
uv run --frozen --project services/ai python evidence/chunking/comparar.py
```

Compara el troceador de producción por sección con ventanas consecutivas de 64 caracteres sin solapamiento sobre el texto extraído de los dos PDF sintéticos de `evidence/fixtures/docs`. Se anotaron manualmente tres hechos literales por documento antes de medir. Cuenta cuántos aparecen enteros en al menos un fragmento; no mide recuperación, respuestas ni latencia. La alternativa conserva títulos y cabeceras, mientras que el troceador de producción los separa del cuerpo, por lo que el recuento de caracteres no es una comparación de tokens equivalente.

| Documento | Estrategia | Fragmentos | Hechos íntegros | Caracteres |
|---|---|---:|---:|---:|
| robot-demo | Secciones | 2 | 3/3 | 95 |
| robot-demo | Fijo, 64 caracteres | 3 | 1/3 | 161 |
| sensor-demo | Secciones | 2 | 3/3 | 98 |
| sensor-demo | Fijo, 64 caracteres | 3 | 1/3 | 166 |

En estos ejemplos, las secciones mantienen juntos los seis hechos y las ventanas fijas parten cuatro. Esto explica una ventaja concreta para citas literales, pero el tamaño de ventana elegido y el conjunto diminuto no permiten concluir que esta estrategia sea mejor en general. Los documentos sin cabeceras numeradas, las secciones largas y las preguntas que necesitan varias secciones necesitan otra evaluación, con recuperación y fuentes aprobadas.
