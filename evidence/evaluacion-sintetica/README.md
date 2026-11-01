# Evaluación sintética de documentos y facturas

Se generaron dos manuales PDF y tres imágenes de factura para esta prueba. Las doce preguntas y sus expectativas se fijaron antes de ejecutarlas. Las imágenes contienen números de factura y cantidades ficticias. La prueba usa los modelos locales y el servicio HTTP; no usa facturas reales ni constituye un gold aprobado.

El oráculo comprueba el tipo de respuesta, la presencia de un valor literal esperado y al menos una cita cuando corresponde. No verifica automáticamente que la cita sostenga toda la respuesta ni mide la calidad de la extracción por campo. La inspección de los resultados aporta el detalle siguiente.

| Casos | Resultado | Observación |
|---|---|---|
| D01–D04 | 4 de 4 cumplen | Respuestas documentales con el valor esperado y citas. |
| D05–D06 | 2 de 2 cumplen | Rechazos para datos ausentes. |
| F01–F04 | 0 de 4 cumplen | Se pidieron importes presentes en las imágenes; las respuestas señalaron que faltaban. |
| F05 | No cumple | Se esperaba aclaración entre dos facturas del mismo emisor; se respondió que faltaba el importe. |
| F06 | Cumple | Se rechazó una factura inexistente. |

Los tres archivos de factura se aceptaron con estado `revisar` y motivo `importes_incompletos`. Sus registros no conservaron los importes sintéticos esperados. Esta observación no identifica por sí sola si el fallo se produjo en el OCR o en la extracción posterior. La batería obtiene 7 coincidencias de 12 con este oráculo limitado; no es una medida general de precisión.

El borrador privado se amplió con 11 de los casos sintéticos y conserva los 44 originales. El caso de aclaración se mantiene aparte porque el esquema original solo distingue preguntas contestables y no contestables. Ningún caso se aprobó y el borrador combinado no se ejecutó contra fuentes reales. El generador y los resultados completos se conservan fuera del repositorio.
