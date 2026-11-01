# Cobertura de requisitos

Requisitos parafraseados del enunciado (no se reproduce el texto original). Estado a fecha del tag más reciente (ver `docs/CHANGELOG.md`).
- **Cumplido**: implementado y con una prueba que lo demuestra.
- **Parcial**: implementado, pero la prueba es de humo o falta una parte.
- **No**: falta.

"Fiabilidad real" dice qué prueba lo respalda. Una prueba con datos sintéticos o simulados no sustituye a la evaluación con un conjunto aprobado, que aún no existe.

## Resumen v0.17.0

- Mejoran el historial local, la revisión de feedback y la visibilidad de fallos; las respuestas conservan su stream aunque falle el guardado.
- Pendientes: gold aprobado, evaluación representativa, aislamiento multiusuario y persistencia de la cola ante reinicios.
- Recuento: 31 filas, 18 cumplidas, 10 parciales y 3 no. Las mejoras no cambian el estado de esas filas.

## Resumen v0.16.0

- Mejoran la correlación de consultas y el cierre de streams incompletos; existen trazas y almacenamiento interno de historial y feedback. Check completo, tres pasadas con axe y humo HTTP sintético con modelos reales correctos.
- Pendientes: conectar historial y feedback con autorización, privacidad, retención e interfaz; medir su coste completo, evaluación representativa y gold aprobado.
- Recuento: 31 filas, 18 cumplidas, 10 parciales y 3 no. Las piezas internas no completan nuevos requisitos de usuario.

## Resumen v0.15.2

- Mejoran la concurrencia, la admisión acotada, los errores y la extracción de importes con dos puntos en una muestra sintética.
- Pendientes: carga sostenida y equidad de la cola, evaluación representativa, gold aprobado y plataformas no probadas. La muestra sintética no acredita precisión general.
- Recuento: 31 filas, 18 cumplidas, 10 parciales y 3 no. La carga nueva no cambia el estado de ninguna fila.

## Resumen v0.15.0

- Mejoran C3, A2 y la evidencia de portabilidad en macOS; el diseño multiusuario sigue siendo una propuesta.
- Pendientes: gold aprobado, evaluación representativa, plataformas no probadas y el error interno observado durante peticiones simultáneas.
- Recuento: 31 filas, 18 cumplidas, 10 parciales y 3 no.

## Consulta documental

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| R1.1 / A4 | Responder solo con el contenido de los documentos | `ask.py` (salida JSON del LLM + `verifier.py`); las citas inline se asignan solo si la frase las sostiene (`inline.py`, ADR-011) | Parcial | Tests unitarios del verificador y de `ask` con LLM falso (218 tests del servicio en la integración). Medido sobre el conjunto de evaluación en borrador (no aprobado): 24/33 contestables respondidas, 11/11 no contestables rechazadas, 0 respuestas sin respaldo (ADR-011). No es una tasa de error: sin gold aprobado no se puntúa la corrección. |
| R1.2 / A3 | Citar el documento y la sección o página | `Citation` en el contrato (`doc`, `section`, `pages`, `doc_id`); marcadores numéricos pegados a la frase y solo las citas que se usan (`segments`, ADR-011) | Cumplido | Tests de API, de `inline` y de las plantillas (una cita por elemento listado; «¿qué facturas tengo?» pasa de 44 citas a 5); e2e de marcadores y vista previa; todas las respuestas con cita llevan marcador (24/24 en la medida). |
| R1.3 | Mostrar el fragmento recuperado | Visor a pantalla completa (`SourceViewer`): página con el fragmento resaltado (`GET /sources/{id}/pages/{n}/highlight`), zoom, arrastre y navegación entre citas | Cumplido | Tests del localizador (`test_highlight.py`), del zoom (`pan-zoom`) y e2e; resaltado comprobado con un PDF real. Las facturas (imagen con OCR) no tienen posiciones: se enseña el campo extraído y el visor lo dice. Capturas `chat-visor-*` y `chat-visor-factura-*` en `evidence/screenshots`. |
| R1.4 / R1.6 | No dar información ajena a los documentos | Rechazo cuando el verificador o el plan SQL no pasan | Parcial | 2 rechazos reales (fuera de dominio y dato ausente) y tests de rechazo. Sin conjunto adversarial ni métrica. |
| R1.5 | Decir explícitamente "no dispongo" | `RefusalNotice` + `reason`; rechazos con `suggestions` (fuentes cercanas reales) y `empty_index` (ADR-009). Desde v0.13.1 una ambigüedad de factura ya no se muestra como rechazo (ADR-013) | Cumplido | e2e "rechazo"; capturas `chat-rechazo-*` (simuladas desde v0.13.3); `e2e/live.spec.ts` contra el stack; e2e y tests de servicio de que una aclaración no es un rechazo. |
| R1.7 | Acreditar la ausencia de alucinaciones | `evidence/` | **No** | El gold está en borrador y no aprobado; las cifras antiguas no valen. Hoy solo hay pruebas de humo. |
| A1 | Ingesta y troceado propios | `ingest.py`, `chunking.py` (por sección, `chunk_id` determinista) | Cumplido | Tests de chunking (secciones, pie de página fuera); ingesta real: 44 fragmentos en 1,8 s. |
| A2 | Justificar el troceado y medirlo | `architecture.md`, `evidence/chunking/` | Parcial | Comparación reproducible en dos PDF sintéticos: secciones conserva 6/6 hechos literales completos y ventanas fijas de 64 caracteres conservan 2/6. No mide recuperación ni generaliza a documentos sin encabezados o secciones largas. |

## Facturas

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| B1 | Subir la imagen de una factura | `POST /invoices/upload?job=`; modal «Añadir fuentes», aviso persistente con el estado real de cada archivo (`GET /ingest/jobs/{id}/events`) y cola `UploadStore` | Cumplido | Tests de API (incluido el 413) y de los eventos de ingesta; e2e de subida con estados, duplicados, fallo y reintento (respuestas simuladas); capturas del aviso con OCR real. El progreso vive en memoria: un reinicio del servicio lo pierde (ADR-011). |
| B2 | Extracción estructurada fiable | `invoice_extract.py`: OCR → reglas Decimal → LLM solo para texto | Parcial | 6/6 facturas **sintéticas** sin discrepancias frente a su JSON. Las facturas reales aún no se han evaluado (lo decide Miguel). |
| B3 | Incorporar las facturas al mismo índice y consultarlas en lenguaje natural | `chunk_invoice` en el mismo índice + `facturas_q` tipada; plan validado y resolución en código (ADR-012) | Cumplido | Baterías propias con LLM real: 36/36 y 33/33 adversariales, 0 falsas (antes 6/36 y 7/33). Contar y sumar en SQL. 2.005 facturas sintéticas: 33 ms de parte determinista. |
| B4 | Diseñar los campos y no inventar ninguno | Campos sin evidencia → `null`; puertas de suma e IVA → "revisar" | Cumplido | `test_review_regressions` (texto sin evidencia → null) y e2e del detalle de factura (campos, motivo e imagen). |
| B5 | No responder nada que no figure en las facturas | Valores y citas solo de facturas seleccionadas por código; ambigüedad → tarjeta «¿De qué factura?» con las candidatas reales (`clarification`, ADR-013); sin caída al RAG | Parcial | 0 respuestas falsas en 84 preguntas (A, B y C, 33 adversariales) y tests de cada regla; tests de servicio y e2e de la aclaración (datos ausentes → sin dato, no inventado). Las baterías son propias y no están aprobadas como gold. |

## Restricciones

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| C1 / N1 | 100 % local, sin APIs de terceros | llama-server en 127.0.0.1 (Ollama opcional) | Cumplido | Todos los adaptadores apuntan a localhost (`config.yaml`). Internet solo en la instalación. |
| C2 | Modelos elegidos para la máquina disponible | `config.yaml`, `assets.json` | Parcial | Funciona en un M4 de 16 GB (humo real). |
| C3 | Especificar el hardware | README "Probado en" | Cumplido | `sysctl`, `sw_vers` y `system_profiler` identifican CPU y GPU de 10 núcleos, 16 GiB de memoria unificada y macOS 26.6.2. Hay una muestra RSS durante una consulta sintética; faltan picos y carga representativa (E-B2). |
| C4 / C5 / E-C1 | Justificar cada modelo frente al hardware, con su cuantización y las alternativas descartadas | `docs/modelos-hardware.md` | **No** | Están inventariados los archivos y sus cuantizaciones. Hay instantáneas RSS y una comparación exploratoria reproducible de 4B y 9B con tres preguntas sintéticas y otra compilación. Faltan picos y una evaluación representativa de alternativas. |

## Escalado

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| S1–S3 / E-C4 | Escalado, despliegue y compromisos | `docs/scaling-deployment.md` | Cumplido | Es documento (así lo pide el enunciado). |

## Entregables

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| E-A1 | Código de calidad, errores controlados, README | `mise run check` (ruff, mypy, 313 tests del servicio y 26 de scripts, contrato, eslint, tsc, build) | Cumplido | `check` OK; revisión independiente triada (ADR-006). |
| E-A2 | Sin scripts sueltos ni notebooks | Servicio + web + tareas mise | Cumplido | Los `scripts/` son las tareas del proyecto, con sus propios tests. |
| E-A3 / E-A4 | Interfaz cuidada: respuesta, fuentes navegables, fragmento | `apps/web` (chat sobre AI SDK, citas inline, visor a pantalla completa, Fuentes, Sistema; ADR-010 y ADR-011); API de streaming con trazas y catálogo de fuentes (`docs/streaming.md`, ADR-009) | Cumplido | Integración: 118 e2e con respuestas simuladas en tres pasadas seguidas; los cuatro tests de fixtures contra stack real se omiten. Esos cuatro se ejecutaron en v0.12.0. Axe sin violaciones serias ni críticas en rutas, temas y modos (incluidos el visor, el diálogo de subida y el aviso); capturas contra el stack real con fuentes sintéticas en tres tamaños y cuatro combinaciones de tema. Desde v0.13.1: tarjeta de aclaración de facturas (teclado, axe en cuatro temas y modos) y vista previa de cita anclada con test de posición; 139 e2e en tres pasadas. No se ha probado con usuarios. |
| E-B1 | Conjunto de evaluación con respuestas esperadas y métricas | — | **No** | El gold no está aprobado. `evidence/live` solo tiene 6 facturas y 5 preguntas, sin métricas agregadas. |
| E-B2 | Latencia, tiempo de ingesta y RAM/VRAM en el hardware real | `evidence/live/results.md` (tiempos) | Parcial | Latencias de 3–6 s por pregunta y 11–18 s por factura; ingesta de 1,8 s. Hay dos instantáneas RSS de los cuatro modelos cargados y una consulta sintética en `docs/modelos-hardware.md`, con una compilación distinta a la del ZIP; faltan pico, carga representativa y desglose GPU. |
| E-B3 | Capturas, incluido el rechazo | `evidence/screenshots/` | Cumplido | Regeneradas con `e2e/capture.mjs` contra el stack real (respuestas, vista previa de cita, respuesta panorámica, rechazo, visor con resaltado, visor de factura, diálogo y aviso de subida, Fuentes, Sistema, Ajustes); galería por versión en `evidence/evolution/`. v0.13.1 añade aclaración, respuesta tras elegir y vista previa de cita (36 capturas sintéticas). |
| E-B4 | Otra evidencia | `docs/reviews/`, `docs/test-audit` (`services/ai/docs`), CHECKPOINT | Cumplido | — |
| E-B5 / REP3 | Evidencia regenerable con un comando | `mise run evidence [--live]` | Cumplido | Ejecutado el 31-oct; las capturas son deterministas. |
| E-C2 / E-C3 | Arquitectura: ingesta y garantía de fundamentación | `docs/architecture.md` | Parcial | Están descritas, pero sin medidas que las respalden (ver A2 y R1.7). |
| REP1 / REP2 | Un comando, versiones fijadas, sin montajes frágiles | mise + `setup` con SHA256 + ZIP | Parcial | Probado en macOS, ZIP con smoke falso. Windows y Linux sin probar en real. El OCR viene en el ZIP (Ollama solo como alternativa). |
| N2 | Documentar las elecciones | `decisions-log.md` | Cumplido | — |
| N3 | Huecos del enunciado decididos | `docs/open-gaps.md` | Cumplido | — |
| N5 | ZIP con código, README y arquitectura | `mise run package` | Parcial | Solo se ha probado el smoke falso, sin modelos. El paquete completo con smoke real está pendiente. |

**Trabajo sin publicar.**
- Mejoran C3 con hardware consultado, A2 con comparación exploratoria sintética, E-B2 con muestras RSS y S1–S3 con una propuesta multiusuario detallada.
- Pendientes: gold aprobado, evaluación de recuperación y comparación de modelos, picos de memoria, recorrido del ZIP y comprobaciones completas; el workflow no se ha ejecutado.
- Recuento de 31 filas: 18 cumplidas, 10 parciales y 3 no. C3 cambia de parcial a cumplido y A2 de no a parcial.

**v0.14.0.**
- Mejoran B3, B4, B5 y E-A3/E-A4 con fichas y tablas derivadas de evidencia, contrato versionado, copia fiel y degradación; E-B3 incorpora comparación y galería. 180 e2e ×3 y batería propia de 35 casos live sin respuestas falsas.
- Pendientes: B5 sigue parcial y E-B1 en "no" hasta el gold aprobado; faltan posiciones OCR y prueba de teclado virtual real. Las fechas conservan su representación almacenada.
- Recuento de 31 filas: 17 cumplidas, 10 parciales y 4 no. No cambia el estado de ninguna fila.

**v0.13.3.**
- Mejoran R1.5 (rechazo con lenguaje llano, sin códigos internos), B3 y B5 (importes es-ES y solo los campos pedidos, con una batería sintética de 35 casos y 0 falsas) y E-B3 (capturas nuevas). No cambia el estado de ninguna fila.
- Pendientes: B5 sigue parcial hasta tener un gold aprobado; E-B1 sigue en "no"; las fechas se muestran como están guardadas.
- Recuento final de 31 filas: 17 cumplidas, 10 parciales y 4 no.

**v0.13.2.**
- Mejoran E-A3/E-A4 y R1.5: la vista previa de una cita ya no tapa el composer cuando la cita está al final del hilo (límite de colisión en el hilo, tests de geometría). E-B3 suma las capturas antes y después. No cambia el estado de ninguna fila.
- Pendientes: B5 sigue parcial hasta tener un gold aprobado; E-B1 sigue en "no"; el humo con modelos reales desde el ZIP está en `_agents/ui6/PROGRESO.md`, no en el repositorio.
- Recuento final de 31 filas: 17 cumplidas, 10 parciales y 4 no.

**v0.13.1 (ADR-013).**
- Mejoran R1.5, B5 y E-A3/E-A4: la ambigüedad de facturas es una aclaración con candidatas reales y la vista previa de cita queda anclada. E-B3 suma las capturas nuevas. No cambia el estado de ninguna fila.
- Pendientes: B5 sigue parcial hasta tener un gold aprobado; E-B1 sigue en "no"; las candidatas de persona para listas, conteos y sumas están sin hacer.
- Recuento final de 31 filas: 17 cumplidas, 10 parciales y 4 no.

**v0.13.0 integrada con v0.12.0 (ADR-011 y ADR-012).**
- Mejoran R1.2, R1.3, B1 y E-A3/E-A4 con las citas inline, el visor y el progreso de v0.12.0; B3 y B5 incorporan el plan v2, SQL y aclaraciones de v0.13.0.
- Pendientes: B5 sigue parcial hasta tener un gold aprobado; E-B1 sigue en "no".
- Recuento final de 31 filas: 17 cumplidas, 10 parciales y 4 no.

**Estado v0.17.0 (31 filas; algunas agrupan varios requisitos): 18 cumplidas, 10 parciales, 3 no (R1.7, C4/C5/E-C1, E-B1).** A2 sigue parcial: la comparación sintética no mide recuperación. Los tres "no" requieren acreditación o justificación de modelos frente al hardware.
