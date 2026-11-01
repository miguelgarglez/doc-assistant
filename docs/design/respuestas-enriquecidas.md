# Respuestas enriquecidas

Estado inicial de v0.14.0, 1 de noviembre de 2026. El commit provisional 59474c0 implementó buena parte de esta propuesta antes de escribirla. Este documento distingue esa base de los cambios pendientes de revisión.

## Problema y límites

Quien consulta una factura necesita leer importes y fechas, comparar filas y abrir su evidencia. El modelo puede proponer la intención, pero nunca escribir los valores de un bloque. Se conservan el plan validado, la resolución SQL y el formato es-ES de v0.13.3. Una pregunta por un campo muestra ese campo. La ficha con emisor, cliente, número, fecha y total corresponde a una petición general de datos de una factura concreta. Un campo ausente queda vacío, sin inferirlo.

## Opciones

| Opción | Origen y contrato | Respaldo y degradación |
| --- | --- | --- |
| A. Cliente y Markdown | La web detecta cifras y reconstruye tablas desde el texto. No cambia OpenAPI. | La heurística pierde el vínculo campo/cita, confunde identificadores con importes y depende de la redacción. Se descarta para facturas. |
| B. Bloques del servicio | El servicio deriva celdas de las filas seleccionadas y sus citas. OpenAPI define una unión por `type`. | Cada valor conserva su evidencia. El Markdown completo permite que un cliente antiguo o un bloque inválido degrade sin perder la respuesta. Es la elegida. |
| C. Híbrido | El servicio envía datos y el cliente infiere bloques o completa lo que falta desde Markdown. | Puede aportar presentación a documentos, pero añade dos caminos para la misma factura y hace difícil demostrar que ninguna celda procede de una inferencia. Se limita a destacar cifras literales en Markdown, sin construir datos. |

## Contrato y flujo elegidos

`InvoiceDB` → plan validado y selección SQL → vista de factura → Markdown, segmentos y bloques → `/ask` o SSE → AI SDK → componentes de lectura.

`key_data` contiene título, documento e items con campo, etiqueta, texto, tipo y posición de cita. `table` contiene columnas tipadas, filas con documento y pregunta de detalle, celdas y un resumen opcional. Las preguntas sugeridas salen de campos presentes que todavía no se mostraron, o de apartados reales recuperados. El cliente no calcula importes ni redacta preguntas.

El contrato añadirá `blocks_version: 1` a la respuesta final y al evento `blocks`. Los campos son aditivos y opcionales para clientes anteriores. Una versión desconocida, una estructura inválida, una celda sin respaldo o una referencia fuera de rango hacen que la web muestre el Markdown verificado completo. `done` es autoritativo y reemplaza cualquier evento previo. Los bloques no se muestran como verificados antes de `done`.

Cada valor no vacío, incluido el número de factura, debe enlazar una cita del mismo documento, campo y valor. Un total calculado debe indicar las citas de sus operandos. Los valores ausentes no llevan cita. El Markdown y los segmentos deben contener toda la información que muestra el bloque para que copiar la respuesta y degradar no pierdan datos ni advertencias.

OpenAPI se exporta desde Pydantic y genera el cliente TypeScript. El check compara ambos artefactos contra git. No se mantendrá un contrato manual paralelo.

## Presentación e interacción

La ficha usa una lista de definiciones y la comparación una tabla semántica. Importes y porcentajes se alinean a la derecha; importes, fechas e identificadores usan `tabular-nums`, sin partir un importe entre líneas. Las tablas anchas se desplazan dentro de su contenedor en móvil. Cada cita mantiene la vista previa y la apertura del visor.

Se reutilizan Table, Badge, Skeleton y Button de shadcn y la composición Artifact, Message y Suggestion de AI Elements. La copia de respuesta conserva Markdown y fuentes; la de tabla entrega TSV. Los atajos se anuncian en Ayuda y no interrumpen la escritura. La espera muestra un skeleton sin datos ficticios. El streaming provisional tiene una entrada breve y queda sujeto a la verificación final. `prefers-reduced-motion` elimina animaciones y desplazamientos suaves.

## Implementado en 59474c0

- Servicio en `domain/invoices/blocks.py` y `application/invoices/`; evento SSE y modelos Pydantic en `api/`.
- Data part `blocks`, renderizadores de ficha y tabla, resaltado literal de cifras, skeleton, copia y atajos.
- Fixtures sintéticas y `blocks.spec.ts`, todavía sin verificar al iniciar esta continuación.

## Pendiente al escribir este diseño

- Versionar el contrato y revisar que todos los valores, identificadores y agregados tengan citas suficientes.
- Corregir la validación del cliente: ahora elimina citas inválidas pero deja el valor visible. La alternativa segura es degradar al Markdown.
- Comprobar equivalencia del Markdown, campos ausentes, listados sin columnas adicionales, resumen y acciones sugeridas.
- Ejecutar unitarios, e2e de bloques, check completo, tres pasadas e2e con axe y batería sintética sin respuestas falsas.
- Capturas sintéticas antes/después, capturas reales aisladas, inspección visual, documentación y auditoría en clon limpio.

No se inicia historial ni feedback. No se cambia extracción ni prompts a partir de material real.

## Cierre de implementación

Se conservó B con bloques de presentación autocontenidos. La revisión independiente pidió un conjunto atómico en el cliente, identidad citada, referencias de suma y fidelidad al copiar notas y columnas. Se implementaron esas correcciones, incluida la deduplicación del número en comparativas. La versión es `blocks_version: 1`; los agregados declaran `operation: "sum"` y sus `refs`. El detalle de verificación y capturas queda en CHECKPOINT y en la revisión de v0.14.0.

Se mantiene como límite la evidencia SQL del valor almacenado. Para citar una región del OCR haría falta guardar posiciones en la ingesta. Este cambio no introduce ese dato ni lo infiere.

La petición general se reconoce solo en formas explícitas como "qué datos tiene la factura" o "datos de la factura" y sin campos concretos. Una petición de datos bancarios conserva el IBAN. La batería acepta suma o desglose ante la frase ambigua "total de las facturas" y comprueba los operandos y el resultado mediante Decimal, sin fijar la redacción de la cabecera.
