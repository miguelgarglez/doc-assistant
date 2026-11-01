# Evaluación sintética de documentos y facturas

Se generaron dos manuales PDF y tres imágenes de factura para esta prueba. Las doce preguntas y sus expectativas se fijaron antes de ejecutarlas. Las imágenes contienen números de factura y cantidades ficticias. La prueba usa los modelos locales y el servicio HTTP; no usa facturas reales ni constituye un gold aprobado.

El oráculo comprueba el tipo de respuesta, la presencia de un valor literal esperado y al menos una cita cuando corresponde. No verifica automáticamente que la cita sostenga toda la respuesta ni mide la calidad de la extracción por campo. La inspección de los resultados aporta el detalle siguiente.

| Casos | Antes | Después | Observación |
|---|---|---|---|
| D01–D04 | 4 de 4 | 4 de 4 | Respuestas documentales con el valor esperado y citas. |
| D05–D06 | 2 de 2 | 2 de 2 | Rechazos para datos ausentes. |
| F01–F04 | 0 de 4 | 4 de 4 | Tras corregir el separador, las respuestas contienen los importes y citas esperados. |
| F05 | No cumple | No cumple | Se esperaba una aclaración. Después de la corrección, la respuesta lista las dos facturas con sus importes y citas. Es una salida distinta de la prevista, no una cifra inventada. |
| F06 | Cumple | Cumple | Se rechazó una factura inexistente. |

En la primera ejecución los tres archivos de factura se aceptaron con estado `revisar` y motivo `importes_incompletos`. El OCR de una de las imágenes conservó las etiquetas y cantidades con dos puntos; el extractor no aceptaba ese separador. Tras corregirlo y repetir la batería, las tres facturas quedaron con estado `ok` y sus totales esperados. Las coincidencias con el oráculo pasaron de 7 a 11 de 12. Son dos ejecuciones sobre una muestra pequeña, no una medida general de precisión.

El caso de aclaración se mantiene aparte porque el esquema binario original solo distingue preguntas contestables y no contestables. Esta batería pequeña se conserva como regresión histórica; la evidencia canónica y reproducible de la entrega está en `evidence/live/`.
