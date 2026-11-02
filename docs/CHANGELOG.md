# CHANGELOG

## v0.19.0 · Entrega final

- Documentación de entrada orientada al evaluador: guía de lectura, arquitectura con diagramas, matriz requisito-evidencia, decisiones y supuestos con plan de mejora.
- El verificador rechaza también afirmaciones sin solapamiento léxico suficiente con las fuentes recuperadas; se añadió una regresión para una cita literal pero irrelevante.
- Evaluación local regenerada con expectativas explícitas: 6/6 facturas sintéticas sin discrepancias en los campos comprobados y 5/5 preguntas con salida y citas esperadas.
- Evidencia visual canónica de chat, rechazo, visor y Sistema; se retiraron galerías duplicadas, diarios, handoffs y revisiones internas.
- ZIP autocontenido probado desde un directorio limpio: setup sin descargas, `mise run check`, ingesta PDF, respuesta con cita, OCR de factura y cierre sin puertos ocupados.
- OpenAPI y cliente generado sin cambios respecto a v0.18.0.

## v0.18.0 · Estructura por responsabilidad

- Servicio organizado en `api`, `application`, `domain` e `infra`, con composición en `bootstrap.py`.
- Test AST para límites y ciclos; features web con API pública protegida por ESLint.
- Suites separadas por ámbito y comprobación de enlaces integrada en `mise run check`.
- Reorganización sin cambios de contrato ni interfaz.

## v0.17.1 · Historial contextual y revisión

- Peticiones recientes en Sistema e historial junto al chat.
- Cola y página de revisión de feedback con redacción y exportación controlada.
- Mejoras de subida para PDF largos, progreso y errores explicativos.

## v0.17.0 · Historial local

- SQLite WAL con retención, búsqueda, borrado y token local entre proxy y API.
- Guardado asíncrono que no altera la respuesta; la cola pendiente sigue siendo volátil.
- Feedback opcional con consentimiento y revisión humana.

## v0.16.0 · Robustez y trazabilidad

- Identificador de petición en HTTP y SSE.
- Trazas por etapa, errores tipados y cierre seguro de streams incompletos.
- Base interna de historial y feedback, conectada en la versión siguiente.

## v0.15.x · Concurrencia y evidencia de hardware

- Cola acotada de consultas, bloqueo de PDFium y errores recuperables.
- Comparaciones exploratorias de troceado y modelos; medidas RSS y latencias sintéticas.
- ZIP completo recorrido en macOS ARM64 con modelos reales.

## v0.14.0 · Respuestas estructuradas

- Fichas y tablas derivadas en el servicio, con citas por dato y degradación a Markdown.
- Importes en formato español y presentación móvil.

## v0.13.x · Consultas fiables de facturas

- Plan validado y resolución en código sobre columnas tipadas.
- Personas, números, roles, fechas y campos normalizados.
- Aclaración estructurada ante ambigüedad y citas solo de filas seleccionadas.

## v0.12.0 · Citas inline y visor

- Marcadores junto a la frase, vista previa y visor a pantalla completa con fragmento resaltado.
- Progreso real de subida y reducción de citas no utilizadas.

## v0.11.0 · Chat y Sistema

- AI SDK y componentes de chat adaptados a Base UI.
- Fuentes, Sistema, trazas y salud por componente.

## v0.10.0 y anteriores · Núcleo

- Streaming verificado, preguntas panorámicas desde metadatos, temas y accesibilidad.
- OCR local, facturas, empaquetado autocontenido, cliente generado y arranque unificado.
