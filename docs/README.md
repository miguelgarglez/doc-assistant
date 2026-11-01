# Índice de documentación

## Entrega

Estos son los documentos normativos para evaluar el estado actual:

| Documento | Pregunta que responde |
|---|---|
| [README principal](../README.md) | ¿Qué hace, cómo se arranca y qué debo abrir primero? |
| [Arquitectura](architecture.md) | ¿Cómo se conectan capas, modelos y flujos de pregunta y factura? |
| [Cobertura de requisitos](requirements-coverage.md) | ¿Dónde se cumple cada punto y cómo se comprueba? |
| [Decisiones](decisions-log.md) | ¿Qué se eligió, qué se descartó y por qué? |
| [Supuestos y huecos](open-gaps.md) | ¿Qué se asumió, cuál es el límite y cómo se cerraría? |
| [Modelos y hardware](modelos-hardware.md) | ¿Por qué esos modelos caben y son razonables en el M4 de 16 GiB? |
| [Escalado y despliegue](scaling-deployment.md) | ¿Cómo evolucionaría a varias plantas y usuarios? |
| [Evidencias](../evidence/README.md) | ¿Qué resultados y capturas existen y cómo se regeneran? |

## Referencia técnica

Material útil para revisar o mantener la implementación, subordinado a los documentos anteriores:

| Documento | Contenido |
|---|---|
| [Contrato de streaming](streaming.md) | Eventos SSE, resultado final y compatibilidad |
| [Estructura del repositorio](repo-structure.md) | Mapa de carpetas y límites de capas |
| [Portabilidad](portabilidad.md) | Plataformas, binarios y contingencias |
| [Sistema de diseño](design-system.md) | Tokens, temas, accesibilidad y patrones |
| [Respuestas enriquecidas](design/respuestas-enriquecidas.md) | Fichas, tablas y degradación a Markdown |
| [Arquitectura multiusuario](design/arquitectura-multiusuario.md) | Propuesta ampliada de SSO, ACL y operación |
| [Persistencia de historial](design/persistencia-historial-feedback.md) | Diseño y límites de historial y feedback |
| [CHANGELOG](CHANGELOG.md) | Evolución por versión |
| [Versionado](versioning.md) | Convención de tags y cierre |

## Evidencia histórica

`evolution-notes/`, `reviews/`, `evidence/comparison-*` y `evidence/evolution/` conservan comparaciones y revisiones de versiones anteriores. Sirven para trazabilidad, pero no sustituyen la arquitectura, cobertura y supuestos finales.

## Comandos

```sh
mise run check
CI=1 pnpm --filter web e2e
mise run evidence
mise run evidence --live
mise run package
```
