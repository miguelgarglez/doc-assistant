# CHANGELOG

Fechas del commit etiquetado (Europe/Madrid). Detalle de pruebas en cada tag (`git tag -n99 vX`) y en `CHECKPOINT.md`. Capturas por versión: `evidence/evolution/README.md`.

## Sin publicar

- Comparación visual sintética con v0.14.0 en tres vistas de escritorio; las parejas son idénticas byte a byte. Repetidas tres pasadas Playwright con Node fijado: 180 aprobadas y cuatro live omitidas por pasada.
- Comparación exploratoria reproducible de Qwen3.5 4B y 9B con tres preguntas sintéticas; no acredita calidad general ni descarta alternativas.

- Comparados dos troceados sobre seis hechos sintéticos: 6/6 íntegros por secciones frente a 2/6 con ventanas fijas. La comparación no mide recuperación.
- Muestras RSS de cuatro modelos cargados y una inferencia sintética con llama.cpp 11960; no son picos ni prueban el ZIP. `mise run check` correcto y tres pasadas Playwright con 180 aprobadas y cuatro live omitidas en cada una.

- Registrados el hardware medido, el inventario de modelos y sus límites, y las decisiones pendientes de aprobación.
- Propuesta multiusuario con permisos por documento, ingesta durable y fases de despliegue. No está implementada.
- La matriz multiplataforma configura puertos aislados. Su workflow no se ha ejecutado.
- Revisión privada del gold en borrador, sin evaluación final. Ninguna fase tiene tag nuevo ni sus comprobaciones de cierre completas.

## v0.14.0 · 2026-11-01
- Respuestas enriquecidas desde el servicio. Ficha general con emisor, cliente, número, fecha y total; preguntas específicas con los campos pedidos. Listados y comparativas como tablas, números y valores con su cita, sumas con operación y referencias de operandos.
- Contrato aditivo `blocks_version: 1`, evento SSE `blocks` y data part tipado. OpenAPI y cliente generados. `done` conserva la instantánea completa; ante una versión desconocida o bloques inválidos, la web muestra el Markdown verificado.
- Importes y fechas con cifras tabulares y sin partir el importe. Acciones sugeridas desde campos existentes o apartados recuperados, copia de respuesta con fuentes y TSV con columnas y notas de revisión. Atajos Alt+C/T y Alt+1 a Alt+3 fuera de campos editables.
- Skeletons durante la espera, streaming provisional con entrada breve y movimiento reducido también en retardos CSS y scroll programático. No se añade historial ni feedback.
- Corregidas la pregunta por número que mostraba un total, la duplicación de esa columna en comparativas y el formato monetario del inventario. La ficha general es estable aunque el plan proponga todos los campos; una petición de datos bancarios conserva el IBAN.
- Probado: `mise run check` con 313 tests del servicio y 26 de scripts, contrato sin deriva, lint, tipos y build. Batería sintética de 84 tests con 35 casos sobre el modelo real, sin respuestas falsas bajo sus oráculos y con sumas comprobadas mediante Decimal. Playwright 180/180 en tres pasadas, con axe sin violaciones serias ni críticas; cuatro pruebas de fixtures live omitidas por pasada.
- [Diseño y alternativas](design/respuestas-enriquecidas.md), ADR-014, [revisión](reviews/respuestas-enriquecidas-v0.14.0.md), [comparación sintética](../evidence/comparison-v0.13.3-v0.14.0/README.md) y [galería](../evidence/evolution/v0.14.0/README.md). Capturas de humo con fuentes privadas conservadas solo en local. La batería propia no sustituye a un gold aprobado ni aporta posiciones OCR.

## v0.13.3 · 2026-11-01
- Los importes de las facturas salen siempre en es-ES, «1.706,60 €», con el formateo hecho en el servicio y no en el modelo. El valor guardado no cambia; la cita enseña lo mismo que el texto.
- La respuesta usa el término de la pregunta («precio final», «importe total», «IVA») y solo los campos pedidos: ya no añade el emisor ni otros datos que nadie preguntó. Una tabla cerrada de campos (`invoice_fields.py`) sustituye a los diccionarios sueltos.
- La tarjeta de rechazo ya no enseña «motivo: llm_unanswerable». Titula lo que pasó y dice qué hacer. El código interno queda en Sistema, en la traza.
- Los puertos de los modelos se configuran con variables de entorno (`DOC_ASSISTANT_LLM_PORT`, `_EMBEDDINGS_PORT`, `_RERANKER_PORT`, `_OCR_PORT`, por defecto 8081-8084) en `scripts/dev.py`, `config/config.yaml`, el humo de `package.py` y `evidence.py`. Un puerto ocupado o inválido corta con un mensaje que dice quién lo usa y qué variable cambiar. README, sección «Puertos».
- Sin cambios de contrato.
- Probado: `mise run check` OK con 298 tests del servicio (la batería sintética de facturas añade 35 casos, con 0 respuestas falsas; con el modelo real 35/35) y 26 de scripts. Playwright 148/148 en tres pasadas con axe sin violaciones serias ni críticas. Capturas `chat-rechazo-*` y `chat-factura-*` con backend simulado.

## v0.13.2 · 2026-10-31
- La vista previa de una cita ya no tapa el composer. Calculaba las colisiones contra la ventana y el composer queda fuera del hilo pero dentro de la ventana, así que una cita al final del hilo se abría hacia abajo y lo cubría (40 px medidos con el kit real, 46 o 47 px en las capturas sintéticas). Ahora el límite de colisión es el elemento de scroll del hilo: la tarjeta se abre hacia arriba, sigue centrada en el marcador y se oculta si este sale del hilo. Si ni arriba ni abajo cabe entera, se ciñe al hilo y desplaza su contenido.
- Sin cambios de contrato ni del servicio.
- Probado: `mise run check` OK con 225 tests del servicio. Playwright 142/142 en tres pasadas con axe sin violaciones serias ni críticas. Los 3 tests nuevos de geometría fallan sin el arreglo y pasan con él. Antes y después con el kit real (solo en local) y con backend simulado (`evidence/comparison-v0.13.1-v0.13.2/`).

## v0.13.1 · 2026-10-31
- Aclaración de facturas con tarjeta propia (ADR-013). Si una pregunta no dice de qué factura habla, el chat enseña «¿De qué factura?» con las candidatas como botones (número, fecha, partes y total, solo si existen). Un clic reenvía la pregunta ya desambiguada. Se mueve con teclado. Antes salía «Sin evidencia suficiente».
- Contrato: nuevo evento SSE `clarification` y `done.clarification` (hasta 5 candidatas con `question`). Una aclaración deja de ser un rechazo. OpenAPI y cliente regenerados.
- Vista previa de cita anclada al marcador: centrada, con margen en los bordes y oculta si el marcador sale del hilo.
- Probado: `mise run check` OK con 225 tests del servicio (7 nuevos). Playwright 139/139 en tres pasadas con axe sin violaciones serias ni críticas. Antes y después contrastados con el kit real, en local.

## v0.13.0 · 2026-10-31
- Facturas en lenguaje natural rehechas (ADR-012):
  - Plan validado por esquema (valor, lista, contar, sumar).
  - Personas y números resueltos en código: tildes, mayúsculas, erratas, NIF con guiones, números parciales o sin ceros.
  - Columnas tipadas e indexadas para fechas e importes, y SQL sobre una lista cerrada de campos.
  - Aclaración «¿te refieres a…?» con candidatas. Si se pregunta un valor, se responde un valor.
  - Citas solo de las facturas seleccionadas.
- Integrada sobre v0.12.0: se conservan las citas inline por elemento, el Markdown de `answer_markup`, el visor y el progreso de subida (ADR-011).
- Migración aditiva e idempotente al abrir `InvoiceDB` (`facturas_q`, `partes_fts`). No cambia `SCHEMA_VERSION` ni el contrato de v0.12.0.
- Probado:
  - `mise run check` OK: 218 tests del servicio, 14 de scripts, contrato sin deriva, lint, tipos y build. Playwright 118/118 en tres pasadas con axe sin violaciones serias ni críticas.
  - 155 tests del servicio en la rama original de facturas.
  - Baterías con LLM real: 36/36 (antes 6/36, 6 falsas) y 33/33 adversariales (antes 7/33, 5 falsas).
  - Índice sintético de 2.005 facturas: 0 falsas y 33 ms de parte determinista (p50).

## v0.12.0 · 2026-10-31
- Respuestas panorámicas con Markdown válido (listas planas, párrafos separados) generado por un único constructor (`answer_markup`) y comprobado con tests sobre el HTML resultante. Se revisaron también factura, capacidades, documento y rechazo.
- Solo se citan las fuentes que sostienen la respuesta: «¿qué facturas tengo?» pasa de 44 citas a 5, una por factura; al terminar se descartan las citas que ninguna frase usa.
- Citas inline: marcadores numéricos pegados a la frase con vista previa al pasar el ratón y el desplegable «N fuentes» debajo. El contrato `done` añade `segments` e `inline`. Por defecto asigna el servicio con reglas verificables; el modo `model` (el LLM emite los segmentos) queda como opción porque en gold-v2 contestó 3 preguntas sin respaldo (ADR-011).
- Visor a pantalla completa con zoom, arrastre, navegación entre citas (←/→) y páginas (↑/↓), Esc para cerrar y el fragmento resaltado en la página (`GET /sources/{id}/pages/{n}/highlight`, sin migración). En facturas muestra el campo extraído y explica que no hay posiciones.
- Añadir fuentes: botón grande y modal con zona de suelta; aviso persistente (Sonner) con el estado real de cada archivo, errores en español con reintento y «Ver en Fuentes». Nuevo `GET /ingest/jobs/{id}/events` (SSE) y parámetro `?job=` en las subidas.
- Probado: `mise run check` correcto (146 tests del servicio, 14 de scripts, contrato sin deriva); Playwright 118 pruebas en tres pasadas seguidas más 4 contra el stack real; axe sin violaciones serias o críticas en rutas, temas y modos; gold-v2 (borrador) sin empeoramiento: 24/33 respondidas, 11/11 rechazadas, 0 sin respaldo; capturas en 1440x900, 1280x720 y 390x844 con fuentes sintéticas.

## v0.11.0 · 2026-10-31
- Chat reconstruido sobre AI SDK (`useChat` con un `ChatTransport` propio para `/ask/stream`) y AI Elements adaptados a Base UI: Prompt Input con adjuntos (pegar o arrastrar PDF o imagen), mensajes con Markdown (Streamdown), traza de pasos plegable, píldoras de cita y fuentes plegables que abren el fragmento, Shimmer, sugerencias, copiar y regenerar. Decisión por componente en ADR-010.
- Layout de aplicación a 100dvh: navegación fija, el hilo es el único scroll, composer anclado; visor de citas lateral (hoja inferior en móvil).
- Sistema: diagrama de piezas (navegador, proxy, servicio, LLM, embeddings, reranker, índice, OCR) con estado y latencia reales, y traza de la última consulta que ilumina cada pieza. Nuevo `GET /health/components` en el servicio.
- Fuentes: tabla ordenable (nombre, tipo, páginas, fragmentos, estado, fecha) con filtro de documentos y facturas, detalle lateral y cola de subida con estados y progreso.
- Servicio: plurales correctos en las etiquetas de los pasos ("1 cita verificada").
- Probado: `mise run check`; Playwright 77 pruebas en tres pasadas más 4 contra el stack real (`LIVE_BASE_URL`); axe sin violaciones serias o críticas en las rutas, temas y modos; capturas reales en 1440x900, 1280x720 y 390x844, cuatro combinaciones de tema y modo (`evidence/screenshots`).

## v0.10.0 · 2026-10-31
- Chat acumulado con SSE, pasos de consulta, tokens provisionales y rechazo inmediato que retira el texto no verificado. Comprobado el paso de eventos por el proxy con un servicio de prueba.
- Fuentes reúne documentos y facturas, con páginas, fragmentos y altas. Ajustes concentra tema y modo. Las preguntas panorámicas responden desde el índice (ADR-009).
- Sistema muestra la arquitectura y reproduce la traza; la salud por pieza queda pendiente del endpoint propuesto.
- Adaptación de patrones AI Elements sobre Base UI y decisión detallada en ADR-008.
- Validación: `mise run check` correcto (88 tests del servicio y 14 de scripts), 69 pruebas Playwright en tres pasadas; axe sin violaciones serias o críticas en las cuatro rutas, ambos temas y modos.

## v0.9.0 · 2026-10-31 15:55
- Sistema de diseño intercambiable: temas `industrial` (default) y `neutral`, modo claro/oscuro, página `/design`, guía en `docs/design-system.md` (ADR-007).
- Chat: atajos de teclado, historial de preguntas en sesión, cancelar con AbortController, copiar respuesta/citas/Markdown, pegar/arrastrar PDF e imagen, regenerar, rechazo con diseño propio, auto-scroll que respeta scroll del usuario, progreso de subida.
- Calidad: e2e de comportamiento + axe (0 violaciones serias/críticas en home y `/design`, ambos temas/modos); capturas theme/design desktop y móvil.
- Revisión independiente (13 hallazgos: foco del diálogo, IME, historial ↑, subidas concurrentes, timeout, persistencia, tema antes del pintado, reduced-motion, portapapeles) aplicada.
- Probado: check OK, e2e 38 passed (3 pasadas seguidas), axe 0 serias/críticas en 8 combinaciones.

## v0.8.0 · 2026-10-31 15:00
- OCR de facturas dentro del ZIP: GLM-OCR GGUF en llama-server :8084 por defecto (setup lo descarga con SHA256); Ollama como alternativa documentada. NOTICE con la licencia y la duda.
- Parser de importes: tipos entre paréntesis, base sin tipo y "TOTAL FACTURA".
- Probado: check OK, e2e 12 passed, `mise run package --smoke real` OK (5,53 GB).

## v0.7.0 · 2026-10-31 14:35
- Visor: recorre todas las páginas de un fragmento citado (#23). CI en push/PR con check + e2e (#19).
- Cierre robusto de procesos huérfanos (#14). Setup/start avisan si el OCR de facturas no está listo (#13, parcial).
- Paquete: textos de licencia en `licenses/`; el smoke real sube una factura y comprueba puertos liberados.
- Probado: check OK (11 tests scripts), e2e 12 passed, `mise run package --smoke real` OK.

## v0.6.1 · 2026-10-31 14:05
- Historial reescrito para publicar (nombre público, fixtures neutros, capturas regeneradas por commit); tags recreados en los commits equivalentes. Galería con nota de regeneración.
- Probado: check OK, e2e 11 passed; auditoría de publicación 0 hallazgos.

## v0.6.0 · 2026-10-31 13:41 · 30ed6f5
- Nombre público doc-assistant; cobertura de requisitos, huecos abiertos y escalado a toda la empresa.

## v0.5.0 · 2026-10-31 13:33 · d0ce091
- Revisión aplicada, facturas en la web, empaquetado y evidencia regenerable; esquema SQLite versionado.

## v0.4.0 · 2026-10-31 13:12 · 3ec2f47
- Auditoría de tests del slice (26 migrados, 55 excluidos a propósito, 0 perdidos).
- Facturas: OCR → reglas Decimal → LLM para texto; puertas de suma/IVA → "revisar"; consultas SQL con cita.
- POST /documents; /ingest confinado. Web: dominio corregido, visor lado a lado, capturas móvil.
- Probado: check (42+5 tests), e2e 6 passed, 6/6 facturas sintéticas sin discrepancias.

## v0.3.0 · 2026-10-31 12:50 · 7068e08
- Web conectada al API real con cliente openapi-fetch; citas abren la página con el fragmento.
- Setup resuelve la carpeta de modelos y no redescarga.
- Probado: check OK, e2e 3 passed, setup --verify sin descargas.

## v0.2.0 · 2026-10-31 12:40 · 5f182b4
- LLM con --reasoning-budget 0. Primera pregunta real extremo a extremo.
- Probado (humo): valor correcto con cita en 7 s; rechazo de precio en 5 s.

## v0.1.0 · 2026-10-31 12:32 · e9ca554
- Monorepo FastAPI + Next/shadcn, mise + scripts Python, llama.cpp b12020 con SHA256, contrato OpenAPI con check de deriva.
- Probado: check OK (29 tests), start + Ctrl-C sin huérfanos.
