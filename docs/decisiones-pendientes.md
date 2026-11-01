# Decisiones pendientes

Estas decisiones requieren la aprobación de Miguel. Las pruebas sintéticas no sustituyen a una evaluación sobre fuentes aprobadas.

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

## Binarios para verificar el ZIP de entrega

- **Decidir:** autorizar la descarga y el uso de los archivos fijados de llama.cpp para el recorrido del ZIP, o facilitar los tres archivos `b12020` ya descargados.
- **Opciones:** permitir al empaquetador descargar los archivos y verificarlos por SHA256; colocar los archivos correspondientes en `vendor/archives/`; aplazar la prueba completa.
- **Recomendación:** usar los archivos fijados y verificar su SHA256 antes de ejecutar el recorrido en puertos propios.
- **Impacto:** la autorización nocturna limita las instalaciones a dependencias de lockfiles. El empaquetador descarga automáticamente binarios ausentes y el setup los instala; por eso no se ha ejecutado el ZIP completo. El `llama-server` disponible en el equipo es de otra compilación y no demuestra el contenido del ZIP.
