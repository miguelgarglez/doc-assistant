# Decisiones pendientes

Estas decisiones requieren la aprobación de Miguel. Las pruebas sintéticas no sustituyen a una evaluación sobre fuentes aprobadas.

## Dependencias para verificar este worktree

- **Decidir:** autorizar la instalación local de las dependencias fijadas en los lockfiles dentro de este worktree.
- **Opciones:** autorizar `pnpm install --frozen-lockfile` y `uv sync --frozen` en este worktree; aportar un entorno local equivalente ya preparado.
- **Recomendación:** usar los lockfiles sin actualizar dependencias y repetir `mise run check` con la configuración del repositorio.
- **Impacto:** los enlaces a dependencias de otro worktree permiten probar, pero Turbopack necesita una raíz temporal ampliada para compilar. El check con esa adaptación pasó; falta comprobar el entorno local sin ella.

## Conjunto de evaluación y criterio de aceptación

- **Decidir:** aprobar los casos, sus respuestas esperadas y las fuentes permitidas, y fijar los umbrales de aceptación de respuestas, rechazos y citas.
- **Opciones:** aprobar el borrador tras revisar cada caso; corregirlo y volver a revisarlo; preparar otro conjunto independiente.
- **Recomendación:** revisar cada caso contra su fuente y reservar casos independientes para evaluar la versión final. Fijar umbrales antes de ejecutar la evaluación.
- **Impacto:** R1.7 y E-B1 no pueden acreditarse con un borrador sin aprobar. R1.1, R1.4, B2 y B5 conservan sus límites actuales hasta tener evidencia pertinente. Ninguna muestra finita demuestra ausencia universal de alucinaciones.

## Privacidad y retención del historial

- **Decidir:** si las trazas pueden guardar preguntas y fragmentos literales, cuánto tiempo se retienen y quién puede leer el feedback.
- **Opciones:** guardar texto para reproducir incidencias; guardar solo identificadores y hashes; elegir la política por despliegue.
- **Recomendación:** política configurable, con acceso restringido y retención explícita; decidir el valor predeterminado según los datos reales de la empresa.
- **Impacto:** guardar texto mejora la reproducción, pero amplía la exposición de información confidencial. El diseño de historial sigue siendo una propuesta y no se implementa hasta cerrar las fases anteriores.

## Alcance de identidad y permisos

- **Decidir:** proveedor de identidad, grupos, responsables de gestionar permisos y requisitos de aislamiento entre departamentos o empresas.
- **Opciones:** despliegue local de un usuario; SSO con permisos por documento; separación adicional por instalación o inquilino.
- **Recomendación:** para varios usuarios, SSO y control de acceso en el servicio y en la recuperación de documentos. Elegir el aislamiento físico o lógico tras definir los límites de confianza.
- **Impacto:** determina el modelo de datos, la operación y las pruebas de aislamiento. El servicio actual no autentica usuarios.

## Arquitecturas fuera del ZIP

- **Decidir:** qué arquitecturas deben poder instalarse sin conexión.
- **Opciones:** mantener el paquete para macOS ARM64, Linux x64 y Windows x64; incluir también macOS x64, Linux ARM64 y Windows ARM64 tras validar sus binarios y dependencias.
- **Recomendación:** fijar la matriz según los equipos de destino y probar cada combinación antes de ampliarla.
- **Impacto:** el ZIP incluye solo los tres primeros archivos b12020. En las demás arquitecturas `setup` necesita descargar el archivo correspondiente; Windows ARM64 tiene además la limitación de `sqlite-vec` documentada. Linux y Windows no se han ejecutado en esta sesión.
