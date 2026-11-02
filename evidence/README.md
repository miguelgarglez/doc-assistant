# Evidencias

Todas las fuentes de esta carpeta son sintéticas y se pueden publicar. No contienen documentos, facturas ni capturas privadas.

## Recorrido recomendado

1. [`live/results.md`](live/results.md): modelos reales, seis facturas, tres respuestas con evidencia y dos rechazos.
2. [`screenshots/chat-visor-1440x900-industrial-light.png`](screenshots/chat-visor-1440x900-industrial-light.png): respuesta, cita y fragmento en su página.
3. [`screenshots/chat-rechazo-1440x900-industrial-light.png`](screenshots/chat-rechazo-1440x900-industrial-light.png): consulta fuera de alcance.
4. [`screenshots/sistema-1440x900-industrial-light.png`](screenshots/sistema-1440x900-industrial-light.png): componentes locales, salud y traza.
5. [`chunking/README.md`](chunking/README.md): comparación de troceado por secciones y ventanas.

## Regeneración

```sh
mise run evidence
```

Ejecuta las pruebas deterministas de Playwright con respuestas simuladas versionadas. Sirve para verificar interfaz, navegación, accesibilidad y presentación, no la calidad de los modelos.

```sh
mise run evidence --live
```

Además de evaluar los modelos con fixtures sintéticos, arranca el stack local y regenera las capturas finales a 1440 × 900: respuesta documental con cita, visor, respuesta de factura, rechazo y vista Sistema.

Arranca los modelos reales, ingiere `evidence/fixtures`, ejecuta el conjunto con expectativas, escribe `live/results.json` y `live/results.md`, y cierra el stack. Requiere haber ejecutado `mise run setup`.

## Qué mide cada pieza

| Evidencia | Qué demuestra | Qué no demuestra |
|---|---|---|
| `live/` | Pipeline real local, citas, rechazos, OCR, campos y tiempos sobre fixtures | Precisión sobre documentación de producción |
| `screenshots/` | Interfaz, estados, fragmentos, rechazo y vista Sistema | Calidad del LLM; usa respuestas deterministas |
| `chunking/` | Integridad literal en dos PDF sintéticos | Recall general |
| `evaluacion-sintetica/` | Regresión que detectó y comprobó una corrección del extractor | Gold independiente |

## Métricas y criterio

Para una pregunta contestable, la corrida live exige:

- `ok=true`;
- presencia del literal esperado;
- al menos una cita.

Para una pregunta fuera de alcance exige:

- `ok=false`;
- mensaje «No dispongo»;
- ninguna cita.

Para una factura compara número, base, IVA, IRPF y total con el JSON esperado y exige estado `ok`. El resultado agregado se publica en los dos formatos.

Una coincidencia en este conjunto pequeño no autoriza a afirmar precisión general. El mecanismo de seguridad se apoya además en verificación, selección tipada y rechazo; el paso de producción es repetir el método sobre un conjunto independiente y representativo.
