# Corrida real con datos sintéticos — 2026-10-31 13:22 CET

Generado por `mise run evidence --live`. Datos: evidence/fixtures (sintéticos). No es la evaluación final.

## Facturas

| fichero | estado | discrepancias | s |
|---|---|---|---|
| factura_001.png | ok | {} | 23.3 |
| factura_011.png | ok | {} | 29.7 |
| factura_021.png | ok | {} | 32.7 |
| factura_031.png | ok | {} | 27.0 |
| factura_041.png | ok | {} | 33.2 |
| factura_051.png | ok | {} | 39.3 |

## Preguntas

| tipo | pregunta | ok | respuesta / motivo | citas | s |
|---|---|---|---|---|---|
| documento | ¿Qué alcance tiene el sensor SX-20? | True | El alcance del sensor SX-20 es de 4 m. | sensor-demo p.[1] | 9.4 |
| documento | ¿Qué temperatura de trabajo admite el sensor? | True | 0 a 50 C | sensor-demo p.[1] | 9.3 |
| factura | ¿Cuál es el importe total de la factura F-2026-001? | True | Factura F-2026-001: importe total: 537.94 | F-2026-001 p.[1] | 6.1 |
| rechazo esperado | ¿Cuál es el precio del robot? | False | llm_unanswerable |  | 5.5 |
| rechazo esperado | ¿Quién ganó el mundial de 2010? | False | llm_unanswerable |  | 5.7 |
