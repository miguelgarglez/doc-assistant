# Cobertura de requisitos

Requisitos parafraseados del enunciado (no se reproduce el texto original). Estado a fecha del tag más reciente (ver `docs/CHANGELOG.md`).
- **Cumplido**: implementado y con una prueba que lo demuestra.
- **Parcial**: implementado, pero la prueba es de humo o falta una parte.
- **No**: falta.

"Fiabilidad real" dice qué prueba lo respalda. Una prueba con datos sintéticos o simulados no sustituye a la evaluación con un conjunto aprobado, que aún no existe.

## Consulta documental

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| R1.1 / A4 | Responder solo con el contenido de los documentos | `ask.py` (salida JSON del LLM + `verifier.py`), ADR en `architecture.md` | Parcial | Tests unitarios del verificador y de `ask` con LLM falso; humo real (`evidence/live`): 2/2 preguntas correctas. El verificador es literal; no hay una tasa de error medida. |
| R1.2 / A3 | Citar el documento y la sección o página | `Citation` en el contrato (`doc`, `section`, `pages`, `doc_id`) | Cumplido | Tests de API y e2e "respuesta con fuente"; humo real con cita de página. |
| R1.3 | Mostrar el fragmento recuperado | `SourceViewer` (fragmento resaltado + imagen de la página) | Cumplido | e2e + capturas `ask-answer-with-source*`. |
| R1.4 / R1.6 | No dar información ajena a los documentos | Rechazo cuando el verificador o el plan SQL no pasan | Parcial | 2 rechazos reales (fuera de dominio y dato ausente) y tests de rechazo. Sin conjunto adversarial ni métrica. |
| R1.5 | Decir explícitamente "no dispongo" | `RefusalNotice` + `reason` | Cumplido | e2e "rechazo"; captura `ask-refusal*`; humo real. |
| R1.7 | Acreditar la ausencia de alucinaciones | `evidence/` | **No** | El gold está en borrador y no aprobado; las cifras antiguas no valen. Hoy solo hay pruebas de humo. |
| A1 | Ingesta y troceado propios | `ingest.py`, `chunking.py` (por sección, `chunk_id` determinista) | Cumplido | Tests de chunking (secciones, pie de página fuera); ingesta real: 44 fragmentos en 1,8 s. |
| A2 | Justificar el troceado y medirlo | `architecture.md` (solo describe) | **No** | No hay una comparación medida de estrategias de troceado en este repo. |

## Facturas

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| B1 | Subir la imagen de una factura | `POST /invoices/upload`, `UploadDropzone` | Cumplido | Tests de API (incluido el 413); e2e de facturas; humo real (6 subidas). |
| B2 | Extracción estructurada fiable | `invoice_extract.py`: OCR → reglas Decimal → LLM solo para texto | Parcial | 6/6 facturas **sintéticas** sin discrepancias frente a su JSON. Las facturas reales aún no se han evaluado (lo decide Miguel). |
| B3 | Incorporar las facturas al mismo índice y consultarlas en lenguaje natural | `chunk_invoice` en el mismo índice + tabla SQL; plan en `/ask` | Cumplido | Humo real: "importe total de F-2026-001" → 537.94 con cita. Los agregados ("suma del IVA de todas") se rechazan. |
| B4 | Diseñar los campos y no inventar ninguno | Campos sin evidencia → `null`; puertas de suma e IVA → "revisar" | Cumplido | `test_review_regressions` (texto sin evidencia → null) y captura `invoice-review*`. |
| B5 | No responder nada que no figure en las facturas | Plan SQL ejecutado por código; un campo nulo o una factura inexistente → rechazo | Parcial | Tests de `run_plan`; aviso cuando la factura está en revisión. Sin evaluación adversarial. |

## Restricciones

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| C1 / N1 | 100 % local, sin APIs de terceros | llama-server en 127.0.0.1 (Ollama opcional) | Cumplido | Todos los adaptadores apuntan a localhost (`config.yaml`). Internet solo en la instalación. |
| C2 | Modelos elegidos para la máquina disponible | `config.yaml`, `assets.json` | Parcial | Funciona en un M4 de 16 GB (humo real). |
| C3 | Especificar el hardware | README "Probado en" | Parcial | Solo dice el chip y la RAM. Faltan la CPU, la GPU/VRAM unificada y la versión del SO, medidas con un comando. |
| C4 / C5 / E-C1 | Justificar cada modelo frente al hardware, con su cuantización y las alternativas descartadas | — | **No** | No está escrito en este repo. |

## Escalado

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| S1–S3 / E-C4 | Escalado, despliegue y compromisos | `docs/scaling-deployment.md` | Cumplido | Es documento (así lo pide el enunciado). |

## Entregables

| Id | Requisito (paráfrasis) | Dónde | Estado | Fiabilidad real |
|---|---|---|---|---|
| E-A1 | Código de calidad, errores controlados, README | `mise run check` (ruff, mypy, 55+7 tests, contrato, eslint, tsc, build) | Cumplido | `check` OK; revisión independiente triada (ADR-006). |
| E-A2 | Sin scripts sueltos ni notebooks | Servicio + web + tareas mise | Cumplido | Los `scripts/` son las tareas del proyecto, con sus propios tests. |
| E-A3 / E-A4 | Interfaz cuidada: respuesta, fuentes navegables, fragmento | `apps/web` | Cumplido | 11 e2e; capturas en escritorio y móvil. No se ha probado con usuarios. |
| E-B1 | Conjunto de evaluación con respuestas esperadas y métricas | — | **No** | El gold no está aprobado. `evidence/live` solo tiene 6 facturas y 5 preguntas, sin métricas agregadas. |
| E-B2 | Latencia, tiempo de ingesta y RAM/VRAM en el hardware real | `evidence/live/results.md` (tiempos) | Parcial | Latencias de 3–6 s por pregunta y 11–18 s por factura; ingesta de 1,8 s. **No se mide la RAM/VRAM.** |
| E-B3 | Capturas, incluido el rechazo | `evidence/screenshots/` | Cumplido | Regeneradas por e2e; galería por versión en `evidence/evolution/`. |
| E-B4 | Otra evidencia | `docs/reviews/`, `docs/test-audit` (`services/ai/docs`), CHECKPOINT | Cumplido | — |
| E-B5 / REP3 | Evidencia regenerable con un comando | `mise run evidence [--live]` | Cumplido | Ejecutado el 31-oct; las capturas son deterministas. |
| E-C2 / E-C3 | Arquitectura: ingesta y garantía de fundamentación | `docs/architecture.md` | Parcial | Están descritas, pero sin medidas que las respalden (ver A2 y R1.7). |
| REP1 / REP2 | Un comando, versiones fijadas, sin montajes frágiles | mise + `setup` con SHA256 + ZIP | Parcial | Probado en macOS, ZIP con smoke falso. Windows y Linux sin probar en real. El OCR viene en el ZIP (Ollama solo como alternativa). |
| N2 | Documentar las elecciones | `decisions-log.md` | Cumplido | — |
| N3 | Huecos del enunciado decididos | `docs/open-gaps.md` | Cumplido | — |
| N5 | ZIP con código, README y arquitectura | `mise run package` | Parcial | Solo se ha probado el smoke falso, sin modelos. El paquete completo con smoke real está pendiente. |

**Resumen (31 filas; algunas agrupan varios requisitos): 17 cumplidas, 10 parciales, 4 no (R1.7, A2, C4/C5/E-C1, E-B1).** Los cuatro "no" son de acreditación y justificación, no de funcionalidad. Se cierran con el conjunto de evaluación aprobado, una medida del troceado y la justificación de los modelos frente al hardware.
