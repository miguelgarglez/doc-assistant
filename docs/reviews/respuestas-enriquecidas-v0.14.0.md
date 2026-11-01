# Revisión de respuestas enriquecidas

Revisión independiente de servicio y UI por dos agentes gpt-6.1-sol y revisión final por un tercer agente gpt-6.1-sol. Diversidad de modelos reducida por el veto explícito a gpt-6-astra. El tercer revisor comprobó las correcciones sobre a94ee60 sin detectar fallos materiales pendientes. La inspección visual y las suites completas se registran en CHECKPOINT.

## Datos y contrato

Se conservaron los bloques autocontenidos frente a un grafo de dominio nuevo. Esa alternativa permitiría evidencia estable por identificador, pero requeriría migrar todos los consumidores. Para esta versión, cada celda tiene una posición de cita del mismo documento, campo y valor; una suma identifica sus operandos y su operación. `done` confirma la versión y la instantánea completa. La web descarta el conjunto si entiende solo parte de él.

Las citas SQL acreditan valores extraídos y almacenados, no una transcripción literal con posiciones del OCR. El visor de factura conserva esa distinción. Las capturas reales solo comprueban presentación y humo; no se usaron para ajustar extracción ni prompts.

## Auditoría de interfaz

Lectura de un chat documental por una persona que necesita comprobar y comparar datos. Se priorizan legibilidad, evidencia próxima y copia fiel. La propuesta conserva una sola representación visible para evitar repetir el mismo importe en texto y tarjeta.

| Before | After | Why |
| --- | --- | --- |
| Cita inválida eliminada, valor conservado | Descartar todos los bloques y mostrar Markdown | No presentar como verificado un dato sin respaldo |
| Tipo desconocido descartado junto a bloques válidos | Alternativa completa si un bloque no se entiende | No ocultar parte de la respuesta |
| Números de fila sin cita | Identificador y marcador junto a la acción de detalle | El número también es evidencia |
| Total sin referencias | Operación suma y referencias de cada operando | Permitir revisar el cálculo |
| TSV de tres columnas con total en la segunda | Misma anchura de fila y total en la última columna | Conservar la alineación al pegar |
| Copia sin notas | Copia con revisión y truncamiento | Conservar las limitaciones de los datos |
| Alt+C/T dentro del editor | Atajos solo fuera de campos editables | Respetar Option en macOS |
| Scroll suave programático con movimiento reducido | Seguimiento instantáneo y streaming sin animación | Respetar la preferencia incluso fuera de CSS |

## Checklist shadcn y AI Elements

- Consultados Table, Badge y Skeleton con la CLI instalada, sin instalar dependencias. Table y Skeleton reutilizan los componentes existentes. Los valores numéricos usan un contenedor literal con `tabular-nums`; no se convierten en etiquetas de estado.
- Consultada la [documentación de Artifact](https://elements.ai-sdk.dev/components/artifact), adaptado sobre Button y Tooltip de Base UI ya usados por el proyecto. Cabecera, acciones y cuerpo están separados.
- Tabla HTML semántica con cabeceras de columna, importes alineados y scroll horizontal interior. Ficha con `dl`, etiquetas y valores.
- Nombres accesibles en controles de copia y acciones de fila. Citas reutilizan el mismo marcador, vista previa y visor.
- Tokens semánticos, dos temas y dos modos. Sin colores crudos ni iconos decorativos nuevos.
- Skeleton decorativo con estado accesible separado. Provisional visible hasta verificación, bloques solo con resultado final.
- Copia de respuesta con Markdown y fuentes; copia tabular con columnas y notas. Ayuda de atajos actualizada.
- Movimiento reducido cubre animaciones, retardos CSS y scroll programático. Teclado responde sin animar el envío.

## Unslop UI

| Rule | Before | After |
| --- | --- | --- |
| U1, U2, U6, U9, U10, U11 en renderizador y mensaje | 0 | 0 |
| U15 y U16, gráficos | No aplica | No aplica |
| unslop 13 en texto de estos componentes | 0 | 0 |

Se conserva el guion de dato ausente porque distingue una celda vacía de un cero. Los chips contienen fechas e importes reales. Se conserva el aviso de revisión porque cambia cómo se debe usar el dato. La nota bajo el compositor sobre verificación se mantiene por continuidad de alcance; puede revisarse en una limpieza global de copy.

## Revisión del cierre

La segunda revisión del cambio de ficha general detectó que "datos bancarios" podía convertirse en un resumen. La política quedó limitada a las formas explícitas de petición general y una regresión sintética conserva únicamente IBAN. También se añadió un oráculo aritmético exacto a las sumas, con una prueba negativa que altera texto y resumen. El revisor independiente reprodujo ambos controles y devolvió un veredicto sin fallos materiales pendientes.

Verificación final: 313 tests de servicio y 26 de scripts en check; batería de 84 tests, incluidos 35 live; tres pasadas de 180 e2e con axe y cuatro pruebas de fixtures live omitidas por pasada. El alcance de "sin falsas" se limita a la batería sintética propia. La revisión visual incluyó las 36 parejas de capturas por hojas de contacto y vistas a tamaño original, dos tablas móviles desplazadas y las capturas locales de humo.
