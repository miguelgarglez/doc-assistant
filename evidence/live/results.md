# Corrida real con datos sintéticos — 2026-11-02 01:18 CET

Generado por `mise run evidence --live`. Los datos y las expectativas están versionados en `evidence/fixtures` y `scripts/evidence.py`. Es una evaluación sintética reproducible, no una medida de precisión sobre documentación de producción.

## Resultado

- Extracción de facturas: **6/6** sin discrepancias en los campos comprobados.
- Preguntas: **5/5** cumplen el tipo de salida, el valor literal y la regla de citas esperados.

## Facturas

| fichero | estado | discrepancias | s |
|---|---|---|---|
| factura_001.png | ok | {} | 13.8 |
| factura_011.png | ok | {} | 20.8 |
| factura_021.png | ok | {} | 21.9 |
| factura_031.png | ok | {} | 20.0 |
| factura_041.png | ok | {} | 30.2 |
| factura_051.png | ok | {} | 39.8 |

## Preguntas

| tipo | pregunta | esperado | resultado | cumple | citas | s |
|---|---|---|---|---|---|---|
| documento | ¿Qué alcance tiene el sensor SX-20? | ok=True; contiene «4 m»; al menos una cita(s) | El alcance del sensor SX-20 es de 4 m. | sí | sensor-demo p.[1] | 15.1 |
| documento | ¿Qué temperatura de trabajo admite el sensor? | ok=True; contiene «0 a 50 C»; al menos una cita(s) | 0 a 50 C | sí | sensor-demo p.[1] | 15.4 |
| factura | ¿Cuál es el importe total de la factura F-2026-001? | ok=True; contiene «537,94»; al menos una cita(s) | - Factura F-2026-001: importe total: 537,94 € | sí | F-2026-001 p.[1] | 9.7 |
| rechazo | ¿Cuál es el precio del robot? | ok=False; contiene «No dispongo»; ninguna cita(s) | No dispongo de esa información en los documentos | sí | — | 8.7 |
| rechazo | ¿Quién ganó el mundial de 2010? | ok=False; contiene «No dispongo»; ninguna cita(s) | No dispongo de esa información en los documentos | sí | — | 7.1 |
