# Versionado

- Tags anotados `vMAJOR.MINOR.PATCH`.
- `MINOR`: capacidad o hito de entrega visible.
- `PATCH`: corrección compatible o documentación.
- Antes de etiquetar: árbol limpio, `mise run check`, e2e si cambia código o interfaz, evidencia actual, paquete probado en limpio y auditoría pública con `TOTAL: 0`.
- El mensaje del tag resume qué cambió, qué se probó y qué límites permanecen.
- `docs/CHANGELOG.md` describe el estado publicado; los diarios y artefactos internos no forman parte de la entrega.
