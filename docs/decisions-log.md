# Decisiones de arquitectura

Esta página recoge las decisiones que explican el producto final. No es un diario: cada entrada indica el problema, la elección, el motivo y el coste aceptado.

## ADR-001 · Dos aplicaciones y un contrato

**Decisión.** FastAPI concentra IA, OCR, recuperación y persistencia; Next.js concentra interfaz y proxy. OpenAPI es la fuente de verdad y genera el cliente TypeScript.

**Por qué.** Python tiene el ecosistema adecuado para PDF, modelos e índice; TypeScript permite una interfaz cuidada sin acoplarla al pipeline. El check de deriva convierte el contrato en una frontera comprobable.

**Coste.** Hay dos runtimes y un proceso adicional. Se compensa con arranque unificado y versiones fijadas.

## ADR-002 · Todo el procesamiento en loopback

**Decisión.** Cuatro servidores llama.cpp y la API escuchan solo en `127.0.0.1`; no se usa inferencia cloud.

**Por qué.** La documentación es sensible y el requisito exige ejecución local. Un único runtime reduce dependencias y permite empaquetar modelos y binarios con SHA256.

**Coste.** La calidad y la concurrencia quedan limitadas por el portátil disponible.

## ADR-003 · Qwen 4B cuantizado como modelo principal

**Decisión.** Qwen3.5 4B Q4_K_M, contexto 8192, dos slots y razonamiento desactivado.

**Por qué.** Debe convivir con embeddings, reranker, OCR, web y API en 16 GiB unificados. El 9B no mostró ventaja en la prueba exploratoria y reduce margen operativo. Q4_K_M es un compromiso entre memoria y calidad; no se eligió la cuantización más pequeña solo por caber.

**Coste.** Un 4B rechaza más y entiende peor formulaciones difíciles. El sistema prefiere ese error seguro a aceptar una respuesta dudosa.

## ADR-004 · Recuperación híbrida y reranking

**Decisión.** Unión de búsqueda vectorial y BM25, seguida de bge-reranker-v2-m3 y top 5.

**Por qué.** Los embeddings cubren paráfrasis; BM25 conserva referencias, códigos y unidades; el reranker limita el contexto que llega al generador.

**Coste.** Un servidor adicional y más latencia. Se acepta porque reduce candidatos irrelevantes antes de la etapa de mayor riesgo.

## ADR-005 · Troceado por estructura

**Decisión.** Extraer por página, detectar secciones y subdividir solo cuando una sección excede el límite. Cada fragmento conserva documento, sección y páginas.

**Por qué.** Una cita debe ser comprensible y navegable. En la comparación sintética, las secciones conservaron 6/6 hechos completos frente a 2/6 con ventanas fijas cortas.

**Coste.** Los PDF sin encabezados o con maquetación irregular pueden necesitar OCR documental o segmentación visual. La comparación no demuestra recall general.

## ADR-006 · Verificar después de generar

**Decisión.** El LLM devuelve JSON con respuesta y referencias. El código valida esquema, existencia de citas, soporte literal y cantidades; si falla, rechaza. El texto provisional se marca y puede retirarse.

**Por qué.** Pedir al modelo «no inventes» no es una garantía. La aceptación debe depender de reglas fuera del modelo.

**Coste.** El verificador heurístico puede rechazar paráfrasis correctas. Se prefiere un falso rechazo a una respuesta sin respaldo.

## ADR-007 · Facturas: modelo para interpretar, código para resolver

**Decisión.** GLM-OCR extrae texto; reglas Decimal capturan importes; Qwen ayuda con campos textuales. Para preguntar, el LLM propone un plan validado y el código resuelve personas, números, filtros, SQL y formato.

**Por qué.** Importes, sumas y selección de filas deben ser deterministas. El modelo no genera SQL libre, no calcula totales y no puede citar una factura que el código no seleccionó.

**Coste.** Las formulaciones y campos admitidos están acotados. Ampliarlos exige añadir vocabulario y tests.

## ADR-008 · Ausente es `null`; incoherente es `revisar`

**Decisión.** No completar campos ausentes. Comprobar suma e IVA; una inconsistencia no se oculta ni se corrige automáticamente.

**Por qué.** Un campo vacío es más honesto que uno plausible pero inventado. Mantener el registro revisable permite consultar lo que sí tiene evidencia.

**Coste.** Algunas facturas quedan parciales y requieren revisión humana.

## ADR-009 · La ambigüedad es una aclaración, no un rechazo

**Decisión.** Si varias facturas encajan, devolver candidatas estructuradas y preguntar «¿De qué factura?».

**Por qué.** Hay evidencia, pero falta intención del usuario. Elegir al azar sería falso y llamarlo «sin evidencia» sería engañoso.

**Coste.** Añade un turno. La elección no se memoriza como estado implícito: la pregunta reenviada incluye el número.

## ADR-010 · mise y scripts Python para reproducibilidad

**Decisión.** mise fija Node, pnpm, Python y uv. Scripts Python coordinan setup, procesos, checks, evidencia y empaquetado.

**Por qué.** El mismo punto de entrada funciona en macOS, Linux y Windows sin depender de Bash, Make o Docker. Docker penalizaría Metal en macOS.

**Coste.** El evaluador debe instalar mise y las dependencias de los lockfiles. Linux y Windows están preparados, pero no verificados físicamente.

## ADR-011 · Interfaz orientada a comprobar

**Decisión.** Citas junto a la frase, vista previa del fragmento, visor de página completa, Fuentes, progreso de ingesta y Sistema con salud y traza.

**Por qué.** La confianza no debe depender de creer al asistente: el usuario puede abrir la fuente exacta sin abandonar el flujo.

**Coste.** En facturas no hay coordenadas OCR y, por tanto, no se resalta un rectángulo sobre la imagen.

## ADR-012 · Evidencia sintética pública

**Decisión.** Versionar PDF, facturas, expectativas y capturas sintéticos; mantener fuera cualquier documento sensible.

**Por qué.** La entrega debe ser reproducible y publicable. Los fixtures permiten comprobar el mecanismo, los rechazos y la extracción sin filtrar propiedad intelectual.

**Coste.** Una muestra sintética no estima precisión de producción. Antes de desplegar se necesita un conjunto independiente y representativo.

## ADR-013 · Instalación local de un usuario

**Decisión.** SQLite, historial local con retención y token efímero entre proxy y API. No se implementan SSO ni ACL.

**Por qué.** El reto pide un núcleo local; multiusuario se describe, no forma parte del producto mínimo.

**Coste.** No debe exponerse la API a una red ni usarse como instalación compartida. El plan de evolución está en [Escalado](scaling-deployment.md).

## ADR-014 · Respuestas enriquecidas derivadas de evidencia

**Decisión.** Fichas y tablas se construyen en el servicio desde las mismas filas y citas que generan la respuesta. Markdown verificado permanece como alternativa.

**Por qué.** La web no debe recalcular importes ni completar campos. Cada dato visible conserva su referencia.

**Coste.** El contrato versiona los bloques; una versión desconocida degrada a Markdown para mantener compatibilidad.
