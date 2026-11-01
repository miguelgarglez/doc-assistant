# Cobertura de requisitos

Esta tabla sigue la numeración del checklist original. **Cumplido** significa que existe implementación o documento y una forma concreta de comprobarlo. **Parcial** significa que el mecanismo existe, pero la evidencia pública es sintética o no permite generalizar. **Pendiente de cierre** se reserva al artefacto final que se genera en la última fase.

Conclusión: el alcance funcional solicitado está implementado. Los límites relevantes no son funciones ausentes, sino la representatividad de la evaluación, la ausencia de posiciones OCR para resaltar facturas y la portabilidad no ejecutada fuera de macOS.

## Consulta documental

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| R1.1 | Respuesta exclusivamente documental | `application/ask/pipeline.py` y `domain/answers/verifier.py` | `mise run test-integration`; `mise run evidence --live` | **Parcial.** La respuesta aceptada necesita citas verificadas; la evaluación pública usa corpus sintético. |
| R1.2 | Documento y sección o página exactos | Tipo `Citation` del contrato; marcadores inline y visor | `mise run check`; `mise run evidence` | **Cumplido.** |
| R1.3 | Fragmento recuperado visible | `features/viewer` y `/sources/{id}/pages/{n}/highlight` | Tests de `highlight`, e2e y `evidence/screenshots/chat-visor-*` | **Cumplido.** En facturas se muestra el campo OCR, sin rectángulo sobre la imagen. |
| R1.4 | No informar fuera de las fuentes | Verificador, rechazo y ruta tipada de facturas | `mise run test-unit`; casos de rechazo de `mise run evidence --live` | **Parcial.** Se acredita en casos versionados, no como garantía matemática universal. |
| R1.5 | Rechazo explícito fuera de alcance | `RefusalNotice`: «No dispongo de esa información…» | Capturas `chat-rechazo-*`; tests de consulta y e2e | **Cumplido.** |
| R1.6 | Tratar una respuesta inventada como fallo | Una salida no verificada se retira y termina en rechazo | Tests SSE de `retract` y verificación | **Cumplido por diseño y tests.** |
| R1.7 | Acreditar la fundamentación | `evidence/live/`, baterías unitarias y de integración | `mise run evidence --live` | **Parcial.** Hay expectativas y métricas reproducibles; falta un conjunto independiente con documentos de producción. |

## Restricción local y hardware

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| C1 | Procesamiento íntegramente local | `config/config.yaml`; cinco procesos en `127.0.0.1` | `mise run start`; vista Sistema | **Cumplido.** Internet solo se necesita para instalar dependencias. |
| C2 | Modelos ajustados a la máquina disponible | `scripts/assets.json`, `scripts/dev.py`, `docs/modelos-hardware.md` | Smoke real y medidas de memoria/latencia publicadas | **Cumplido.** |
| C3 | Hardware explícito | README, sección «Hardware de prueba» | Comandos `sw_vers`, `sysctl` y `system_profiler` publicados | **Cumplido.** M4, CPU/GPU de 10 núcleos y 16 GiB unificados. |
| C4 | Justificar modelos, cuantización y viabilidad | `docs/modelos-hardware.md` | Inventario SHA256, muestra RSS y comparación 4B/9B | **Cumplido.** La comparación de calidad es exploratoria y se declara como tal. |
| C5 | Vincular dimensionamiento al hardware real | `docs/modelos-hardware.md` | Medidas y presupuesto simultáneo sobre el M4 de 16 GiB | **Cumplido.** No se presenta la instantánea RSS como pico. |

## Ingesta documental

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| A1 | Extracción, troceado e indexación propios | `application/ingest/service.py`, `domain/documents/chunking.py` | Tests de chunking e ingesta; `mise run evidence --live` | **Cumplido.** |
| A2 | Estrategia de troceado justificada | Arquitectura y `evidence/chunking/` | `uv run --project services/ai python evidence/chunking/comparar.py` | **Parcial.** Secciones conservan 6/6 hechos frente a 2/6 con ventanas; no mide recall sobre un corpus representativo. |
| A3 | Fuente exacta y fragmento junto a respuesta | Contrato, chat y visor | E2E de cita, vista previa y página resaltada | **Cumplido.** |
| A4 | Garantía de fundamentación aplicable | Mismo flujo que R1.1–R1.7 | Tests del verificador y evidencia live | **Parcial** por el límite descrito en R1.7. |

## Facturas

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| B1 | Cargar imagen de factura | `/invoices/upload`, modal «Añadir fuentes» y progreso SSE | Tests API/e2e; `mise run evidence --live` | **Cumplido.** |
| B2 | Extracción estructurada fiable | `application/invoices/extract.py`: OCR, Decimal, texto y puertas aritméticas | Seis facturas con JSON esperado en `evidence/fixtures` | **Parcial.** 6/6 sintéticas sin discrepancias; no se publica una evaluación de facturas reales. |
| B3 | Incorporación al mismo índice y consulta natural | `chunk_invoice`, `facturas_q` y plan validado | Baterías de facturas; pregunta live con cita | **Cumplido.** |
| B4 | Campos definidos y ausencias sin invención | Campos ausentes `null`; suma/IVA incoherentes → `revisar` | Tests de regresión, campos y aritmética | **Cumplido.** |
| B5 | Fundamentación también en facturas | SQL sobre columnas cerradas; citas solo de filas seleccionadas; aclaración ante ambigüedad | Baterías unitarias/live y e2e de aclaración | **Parcial.** Las baterías son propias y sintéticas. |

## Escalado y despliegue

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado |
|---|---|---|---|---|
| S1 | Varias plantas y muchos usuarios | `docs/scaling-deployment.md` | Revisión documental | **Cumplido** como diseño, que es lo solicitado. |
| S2 | Estrategia on-premise y/o nube | `docs/scaling-deployment.md` | Revisión documental | **Cumplido.** |
| S3 | Compromisos de diseño | Tabla de límites y fases en el mismo documento | Revisión documental | **Cumplido.** |

## Entregables

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| E-A1 | Código estructurado, errores y README | Monorepo por capas, errores tipados y README | `mise run check` | **Cumplido.** |
| E-A2 | No entregar scripts aislados ni notebooks | Servicio instalable, web y tareas de proyecto | Inventario del ZIP; no hay notebooks | **Cumplido.** `scripts/` contiene orquestación probada, no el producto aislado. |
| E-A3 | Interfaz usable con respuesta, fuentes y fragmento | `apps/web`: Chat, Fuentes, Sistema y visor | Playwright + axe; capturas | **Cumplido.** |
| E-A4 | Estética sin comprometer fiabilidad | Texto provisional marcado y retirada si falla verificación | Tests del transporte SSE y e2e | **Cumplido.** |
| E-B1 | Preguntas, respuestas esperadas y métricas | Expectativas en `scripts/evidence.py`; resultados en `evidence/live/` | `mise run evidence --live` | **Cumplido con alcance sintético.** |
| E-B2 | Latencia, ingesta y RAM/VRAM en hardware real | `docs/modelos-hardware.md` y `evidence/live/results.md` | Comando live y método publicado | **Cumplido con límites.** En Apple Silicon la VRAM no es separable de la RAM unificada; se publican RSS, no picos. |
| E-B3 | Evidencia visual, incluido rechazo | `evidence/screenshots/` | `mise run evidence` | **Cumplido.** |
| E-B4 | Evidencia adicional | Comparación de chunking, tests, galería y corrida live | Comandos enlazados desde `evidence/README.md` | **Cumplido.** |
| E-B5 | Evidencia regenerable | Tarea `evidence` y fixtures versionadas | `mise run evidence`; `mise run evidence --live` | **Cumplido.** |
| E-C1 | Arquitectura: modelos frente a hardware | `docs/architecture.md` y `docs/modelos-hardware.md` | Revisión de inventario, alternativas y medidas | **Cumplido.** |
| E-C2 | Arquitectura: ingesta y troceado | `docs/architecture.md` | Diagrama y comparación de chunking | **Cumplido.** |
| E-C3 | Arquitectura: fundamentación | `docs/architecture.md` | Diagrama, tests y corrida live | **Cumplido con el límite de R1.7.** |
| E-C4 | Arquitectura: escalado opcional | `docs/scaling-deployment.md` | Revisión documental | **Cumplido.** |

## Reproducibilidad y normas

| ID | Qué se exige | Dónde se cumple | Evidencia reproducible | Estado y límite |
|---|---|---|---|---|
| REP1 | Arranque con un comando o pocos pasos | `mise install`, `mise run setup`, `mise run start` | Smoke del paquete en limpio | **Cumplido en macOS ARM64.** |
| REP2 | Sin montajes manuales frágiles | Versiones fijadas, SHA256, modelos y binarios en el ZIP | `mise run package --smoke real` | **Parcial.** Windows y Linux están empaquetados pero no probados físicamente. |
| REP3 | Evidencia con la misma facilidad | Tarea `evidence` | Comandos anteriores | **Cumplido.** |
| N1 | IA permitida en desarrollo; procesamiento local | Configuración local | Vista Sistema y health checks | **Cumplido.** |
| N2 | Elecciones documentadas | `docs/decisions-log.md` | Índice de decisiones | **Cumplido.** |
| N3 | Resolver huecos deliberados | `docs/open-gaps.md` | Tabla de supuestos, razón, límite y mejora | **Cumplido.** |
| N4 | Priorizar razonamiento sobre amplitud | Alcance y límites declarados | README y supuestos | **Cumplido como criterio de alcance.** |
| N5 | ZIP con código, README y arquitectura | `scripts/package.py` | Inspección y smoke real del ZIP | **Pendiente de cierre** en la fase de empaquetado final. |

## Lectura correcta de la evidencia

- Los fixtures son sintéticos para poder publicarlos y regenerarlos. Sirven para demostrar el mecanismo y detectar regresiones; no estiman la precisión sobre cualquier manual o factura.
- «0 respuestas sin respaldo» en una batería finita no equivale a prometer cero errores universales. La defensa es estructural: evidencia primero, verificación después y rechazo seguro.
- El siguiente paso para producción es acordar un conjunto independiente y representativo, ejecutarlo sin ajustar el sistema con sus respuestas y fijar umbrales de aceptación.
