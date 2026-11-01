# Supuestos y huecos

El enunciado deja decisiones abiertas. Esta página separa qué se asumió, por qué es razonable, qué queda fuera y cómo se cerraría antes de producción.

| Supuesto o hueco | Decisión y razón | Qué queda fuera | Plan de mejora |
|---|---|---|---|
| «Ausencia de alucinaciones» | Se interpreta como una propiedad operacional: ninguna respuesta se acepta sin evidencia recuperada y verificada; ante duda se rechaza. Una muestra finita no prueba ausencia universal. | No existe una garantía formal de implicación semántica ni una tasa general sobre documentos desconocidos. | Acordar un gold independiente, incluir preguntas adversariales y bloquear cambios que introduzcan respuestas sin respaldo. |
| Corpus de evaluación | Se publican fixtures y expectativas sintéticos para que cualquier evaluador pueda repetirlos sin recibir información sensible. | No representan toda la variedad de manuales o facturas de una planta. | Muestrear por tipo de documento, idioma, maquetación y calidad de escaneo; separar conjunto de ajuste y conjunto ciego. |
| Idioma | Interfaz, reglas y mensajes en español; modelos multilingües para tolerar documentación técnica en otros idiomas. | Las reglas de intención y campos no tienen cobertura equivalente en todos los idiomas. | Detectar idioma y ampliar baterías antes de declarar soporte multilingüe. |
| Fuente exacta | Documento, sección, página y fragmento literal. En PDF con capa de texto se resalta el fragmento. | Las facturas OCR no conservan coordenadas; se muestra el valor extraído, no su caja en la imagen. | Guardar bounding boxes del OCR y enlazar cada campo con su región. |
| PDF escaneado | El flujo documental presupone PDF con texto extraíble. | OCR documental completo y reconstrucción de tablas complejas. | Detectar páginas sin texto y pasarlas por OCR local, conservando página y cajas. |
| Troceado | La sección es la unidad semántica; se subdivide cuando es larga. | Documentos sin encabezados, dos columnas irregulares o tablas extensas pueden fragmentarse mal. | Añadir detección de layout y medir recall por tipo de documento. |
| Campos de factura | Número, fecha, emisor, cliente, NIF, base, IVA, IRPF, total e IBAN cuando aparece. Ausente = `null`. | Esquemas fiscales de otros países y líneas de producto detalladas. | Esquema configurable por organización y validadores por país. |
| Factura incoherente | Se conserva en estado `revisar` con motivo; no se corrige ni descarta. | Flujo de aprobación contable o edición manual. | Cola de revisión con auditoría y doble validación antes de activar el dato corregido. |
| Fecha no reconocida | Se conserva el literal; la fecha normalizada queda nula y no participa en filtros. | Interpretación probabilística de formatos desconocidos. | Incorporar formatos aprobados por el cliente y pedir confirmación en revisión. |
| Usuario objetivo | Una instalación local para una persona. El token entre proxy y API protege rutas locales, no identifica usuarios. | SSO, roles, ACL, aislamiento por planta y auditoría corporativa. | OIDC en el BFF, identidad firmada, filtro de permisos antes de recuperar y pruebas de aislamiento. |
| Persistencia | SQLite y cola de escritura en memoria son suficientes para el recorrido local. | Alta disponibilidad y recuperación de pendientes tras reinicio. | Postgres y cola durable antes de desplegar varias réplicas. |
| Concurrencia | Dos consultas activas y cuatro en espera por proceso. | Capacidad sostenida, equidad y coordinación entre procesos. | Prueba de carga representativa y cola compartida con límites por usuario. |
| Plataformas | Verificación completa en macOS ARM64. El ZIP incluye binarios de Linux x64 y Windows x64. | No se ha ejecutado el recorrido real en esas dos plataformas. | Ejecutar setup, check, arranque, demo y cierre en máquinas limpias de cada sistema. |
| Hardware objetivo | El M4 de 16 GiB es la máquina real disponible y condiciona Qwen 4B Q4_K_M. | No se dimensiona un servidor de producción ni se promete un SLA. | Repetir calidad, latencia y pico de memoria en el hardware de cada planta antes de elegir modelo o réplicas. |
| Texto provisional | Puede mostrarse durante el streaming, siempre marcado como «verificando»; `done` puede retirarlo. | Un usuario puede leer durante unos segundos texto que finalmente no se acepta. | Ofrecer un modo conservador que retenga texto hasta verificar si el contexto operativo lo exige. |
| Historial y feedback | Activos localmente con 30 días de retención configurable; el feedback solo copia contexto con consentimiento y exige revisión. | Validación legal, política corporativa y clasificación de datos. | Revisión de privacidad por despliegue, cifrado, roles y retención central. |

## Qué sí se puede afirmar

- El flujo completo funciona localmente en el hardware descrito.
- Las respuestas aceptadas por las pruebas publicadas llevan citas; los casos fuera de alcance publicados se rechazan.
- Las seis facturas sintéticas de la corrida live coinciden en los campos comprobados.
- OpenAPI, cliente, tests, capturas y paquete tienen comandos reproducibles.

## Qué no se afirma

- Precisión general sobre cualquier documento o factura.
- Cero errores universal.
- Soporte de producción multiusuario.
- Compatibilidad verificada en sistemas distintos de macOS ARM64.
- Un SLA de latencia o capacidad.

## Orden de mejora

1. Gold independiente y representativo, con umbrales de fundamentación, recuperación y extracción por campo.
2. Posiciones OCR y OCR de PDF escaneado.
3. Pruebas físicas de Linux y Windows.
4. SSO, ACL antes de recuperar, Postgres y cola durable.
5. Medición de carga y dimensionamiento por planta.
