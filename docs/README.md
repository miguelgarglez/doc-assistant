# Índice de documentación

## Qué documento responde a qué pregunta

| Pregunta | Documento |
|---|---|
| ¿Cómo se conectan los componentes y flujos? | [Arquitectura](architecture.md) |
| ¿Qué se decidió y por qué? | [Decisiones y ADR](decisions-log.md) |
| ¿Cómo se transmiten y verifican las respuestas? | [Streaming y contrato](streaming.md) |
| ¿Cómo se presenta la interfaz? | [Sistema de diseño](design-system.md) y [respuestas enriquecidas](design/respuestas-enriquecidas.md) |
| ¿Cómo podría atender a varios usuarios? | [Escalado](scaling-deployment.md) y [propuesta multiusuario](design/arquitectura-multiusuario.md) |
| ¿Qué sistemas se han probado y cuáles faltan? | [Portabilidad](portabilidad.md) |
| ¿Qué modelos y hardware se usan? | [Modelos y hardware](modelos-hardware.md) |
| ¿Qué requisitos están cubiertos? | [Cobertura de requisitos](requirements-coverage.md) |
| ¿Qué supuestos y huecos se han resuelto? | [Huecos y decisiones](open-gaps.md) |
| ¿Qué decisiones siguen pendientes? | [Decisiones pendientes](decisiones-pendientes.md) |
| ¿Qué cambió en cada versión? | [CHANGELOG](CHANGELOG.md) y [notas por versión](#notas-por-versión) |
| ¿Cuál es el estado y qué se comprobó? | [CHECKPOINT](CHECKPOINT.md) |
| ¿Dónde están las evidencias? | [Corrida sintética](../evidence/live/results.md), [evaluación sintética](../evidence/evaluacion-sintetica/README.md) y [galería](../evidence/evolution/README.md) |
| ¿Dónde está cada pieza del repo? | [Estructura](repo-structure.md) |
| ¿Cómo se versiona? | [Versionado](versioning.md) |
| ¿Cuál fue la propuesta inicial de historial y feedback? | [Propuesta de persistencia](design/persistencia-historial-feedback.md) |

## Estado actual

- La versión de comportamiento sigue siendo v0.17.1; v0.18.0 reorganiza el código sin cambiar el contrato ni la interfaz.
- La [cobertura](requirements-coverage.md) registra 18 cumplidas, 10 parciales y 3 no.
- El servicio usa capas `api`, `application`, `domain` e `infra`, comprobadas con `ast`; la web agrupa seis features y ESLint protege sus APIs públicas.
- Los tests del servicio se dividen en 126 unitarios, 280 de integración y 35 live optativos.
- Hay respuestas con citas, aclaraciones de facturas y bloques derivados de evidencia, con Markdown como alternativa.
- La cola acota consultas por proceso; no limita ingestas ni comparte capacidad entre procesos.
- Faltan gold aprobado y evaluación representativa; los resultados sintéticos no acreditan precisión general.
- No están verificadas la carga sostenida ni la equidad de la cola, ni la causa del error histórico sin traza.
- Linux y Windows siguen sin probar; el check registrado reutilizó dependencias y una raíz temporal ampliada para el build.
- El historial persistente funciona localmente; multiusuario y SSO siguen sin implementar.
- Los límites y el progreso de subida se explican en las [notas de v0.17.1](evolution-notes/v0.17.1.md#subida-de-archivos).

## Orden de lectura

Para evaluar la entrega:

1. [Arranque y límites](../README.md).
2. [Cobertura](requirements-coverage.md) y [estado de un vistazo](CHECKPOINT.md#estado-de-un-vistazo).
3. [Evidencia sintética y límites](../evidence/evaluacion-sintetica/README.md) y [galería](../evidence/evolution/README.md).
4. [Huecos](open-gaps.md), [pendientes](decisiones-pendientes.md) y [portabilidad](portabilidad.md).

Para desarrollar:

1. [Estructura](repo-structure.md) y [arquitectura](architecture.md).
2. [ADR](decisions-log.md) y [contrato SSE](streaming.md).
3. [Diseño](design-system.md) y [bloques de respuesta](design/respuestas-enriquecidas.md).
4. [Escalado](scaling-deployment.md), [pendientes](decisiones-pendientes.md) y [versionado](versioning.md).

## Decisiones de arquitectura

- [ADR-001 Monorepo con dos servicios](decisions-log.md#adr-001-monorepo-con-dos-servicios-2026-10-31).
- [ADR-002 shadcn/ui sobre Base UI](decisions-log.md#adr-002-shadcnui-sobre-base-ui-2026-10-31).
- [ADR-003 Orquestación: mise + pnpm workspace + uv + scripts Python](decisions-log.md#adr-003-orquestación-mise--pnpm-workspace--uv--scripts-python-2026-10-31--decidido-miguel-t175).
- [ADR-004 llama.cpp fijado por tag y SHA256](decisions-log.md#adr-004-llamacpp-fijado-por-tag-y-sha256-2026-10-31).
- [ADR-005 Arreglos sobre la salida de los ayudantes](decisions-log.md#adr-005-arreglos-sobre-la-salida-de-los-ayudantes-2026-10-31).
- [ADR-006 Revisión independiente](decisions-log.md#adr-006-revisión-independiente-codex-gpt-61-sol-y-triaje-2026-10-31).
- [ADR-007 Temas CSS e AI Elements ligeros](decisions-log.md#adr-007-temas-css-e-ai-elements-ligeros-2026-10-31).
- [ADR-008 Chat con SSE, fuentes y vista de sistema](decisions-log.md#adr-008-chat-con-sse-fuentes-y-vista-de-sistema-2026-10-31).
- [ADR-009 Streaming verificado al final y preguntas panorámicas desde el índice](decisions-log.md#adr-009-streaming-verificado-al-final-y-preguntas-panorámicas-desde-el-índice-2026-10-31).
- [ADR-010 Chat sobre AI SDK y AI Elements adaptados a Base UI](decisions-log.md#adr-010-chat-sobre-ai-sdk-y-ai-elements-adaptados-a-base-ui-2026-10-31).
- [ADR-011 Citas inline, visor a pantalla completa y subida con progreso real](decisions-log.md#adr-011-citas-inline-visor-a-pantalla-completa-y-subida-con-progreso-real-2026-10-31).
- [ADR-012 Consultas de facturas: plan validado, resolución en código y aclaración](decisions-log.md#adr-012-consultas-de-facturas-plan-validado-resolución-en-código-y-aclaración-2026-10-31).
- [ADR-013 Aclaración de facturas como evento propio y vista previa de cita anclada](decisions-log.md#adr-013-aclaración-de-facturas-como-evento-propio-y-vista-previa-de-cita-anclada-2026-10-31).
- [ADR-014 Bloques de respuesta derivados de evidencia](decisions-log.md#adr-014-bloques-de-respuesta-derivados-de-evidencia-2026-11-01).

## Notas por versión

- [v0.17.1 · Historial contextual y revisión](evolution-notes/v0.17.1.md)

- [v0.17.0](evolution-notes/v0.17.0.md): historial local, feedback y revisión.
- [v0.16.0](evolution-notes/v0.16.0.md): identidad de petición y piezas internas de historial y feedback.

- [v0.14.0](evolution-notes/v0.14.0.md): bloques de respuesta y evidencia versionada.
- [v0.15.0](evolution-notes/v0.15.0.md): recorrido del ZIP, hardware y límites de portabilidad.
- [v0.15.1](evolution-notes/v0.15.1.md): concurrencia, cola y errores recuperables.
- [v0.15.2](evolution-notes/v0.15.2.md): importes con dos puntos y repetición sintética.
- Notas anteriores: [v0.13.0](evolution-notes/v0.13.0.md), [v0.13.2](evolution-notes/v0.13.2.md) y [v0.13.3](evolution-notes/v0.13.3.md).

## Convenciones

- Los tags de versión son anotados, con formato `vMAJOR.MINOR.PATCH`. [Versionado](versioning.md) define su cierre y auditoría.
- Cada resultado indica versión, método y límites. El diario conserva las comprobaciones históricas; no todas describen el estado actual.
- Las capturas reproducibles van en `evidence/screenshots/`; las galerías por tag, en `evidence/evolution/`; las comparaciones, en `evidence/comparison-*/`.
- Las evidencias públicas usan fuentes sintéticas. Los documentos, las facturas y las capturas privadas permanecen fuera del repositorio y del ZIP.
- `mise run evidence` regenera capturas; `mise run evidence --live` necesita modelos locales. Las pruebas simuladas no demuestran precisión del modelo.
