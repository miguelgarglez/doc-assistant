# Versionado

- Tags **anotados** `vMAJOR.MINOR.PATCH`, semver 0.x, se empujan al repo público solo tras pasar la auditoría de publicación (0 hallazgos).
- **Cuándo se saca un tag:** al cerrar un hito del CHECKPOINT que esté fusionado en `main` y con `mise run check` en verde (y `pnpm e2e` si toca la web). Un tag por hito, sobre el commit que lo cierra.
  - MINOR: capacidad nueva visible (nuevo flujo, endpoint, empaquetado).
  - PATCH: solo correcciones sin cambio de comportamiento esperado.
- **Mensaje del tag:** título + "Qué cambió" + "Qué se probó", copiado de `git log` y del CHECKPOINT. Nada que no conste ahí.
- Al etiquetar: añadir la entrada en `docs/CHANGELOG.md` y regenerar la galería con `mise run evolution` (también la regenera `mise run evidence`).
- Las fechas que se muestran son las del commit etiquetado (Europe/Madrid); los tags v0.1.0–v0.4.0 se crearon a posteriori, el 31-oct hacia las 13:35, sobre sus commits.
