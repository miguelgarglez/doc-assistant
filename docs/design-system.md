# Sistema de diseño (apps/web)

Capas: **tokens semánticos** → **primitivas UI** (`components/ui`) → **componentes de dominio** (`components/domain`, `components/ai`) → **páginas**.

## Temas

Cada tema es un fichero CSS en `apps/web/src/themes/<nombre>.css` que declara variables bajo `[data-theme="<nombre>"]` y su variante oscura `[data-theme="<nombre>"].dark`.

Tokens habituales:

- Color: `--background`, `--foreground`, `--primary`, `--muted`, `--border`, `--highlight`, …
- Tipografía: `--font-family-sans`, `--font-family-heading`, `--font-family-mono` (las familias reales se cargan en `app/layout.tsx` como variables `--font-*`)
- Forma: `--radius`
- Elevación: `--shadow-panel`
- Motion: `--ease-out`, `--ease-in-out`, `--duration-fast`, `--duration-ui`
- Densidad / atmósfera: `--space-density`, `--surface-grid`, `--surface-grid-size`
- Dominio: `--refusal-*`, `--ok-*`, `--review-*`

Temas incluidos:

- `industrial` (por defecto): grafito, acento azul-señal, rejilla sutil, radios cortos
- `neutral`: tipografía distinta, radios amplios, sin rejilla (sirve para validar el swap)

El documento HTML lleva `data-theme` y la clase `dark` cuando el modo es oscuro. El selector de tema/modo está en Ajustes y persiste en `localStorage`.

## Cómo crear un tema nuevo

1. Copia `apps/web/src/themes/neutral.css` a `apps/web/src/themes/<nombre>.css`.
2. Renombra el selector a `[data-theme="<nombre>"]` (y la variante `.dark`).
3. Ajusta colores, radios, tipografía y motion. Si necesitas otra familia tipográfica, regístrala en `app/layout.tsx` y apúntala desde el CSS del tema.
4. Importa el fichero en `app/globals.css`.
5. Añade el nombre a `THEME_NAMES` en `src/lib/theme.ts` y la etiqueta en `themeLabel`.
6. Comprueba ambos modos en `/design` y en la consulta.

## Página `/design`

Muestra swatches, tipografía y componentes clave en el tema/modo activos. Úsala para revisar contraste y coherencia antes de tocar flujos.

## Componentes de chat

Desde v0.11 el chat usa AI SDK y componentes de AI Elements copiados a `components/ai-elements` y adaptados a Base UI (ADR-010). La lógica de la conversación vive en `lib/chat` y `components/providers/chat-provider.tsx`; `components/chat` solo compone la vista.

## Navegación y chat v0.10

La navegación da acceso a Chat, Fuentes, Ajustes y Sistema. En pantallas pequeñas se recoge en un menú. El compositor permanece al pie; las preguntas anteriores se conservan durante la sesión. Los tokens SSE son provisionales hasta el evento final y no ofrecen acciones de copia. Si el servicio retira una respuesta, se elimina el texto provisional.

Fuentes reúne los PDF y las imágenes de facturas. El catálogo muestra su estado, páginas y fragmentos; los fragmentos y las páginas se pueden inspeccionar. Sistema muestra las piezas y la traza compartida de la última consulta, con reproducción. Si no hay endpoint de salud por pieza, el estado se muestra como no medido.

Los patrones de AI Elements se detallan en ADR-008. `Message` y `Trace` adaptan código del registro shadcn al sistema de tokens existente; `Conversation`, sugerencias y acciones se mantienen.

## Layout de aplicación v0.11

El shell ocupa `100dvh`: navegación fija a la izquierda (se pliega en móvil), contenido a la derecha. El único scroll del chat es el hilo (`Conversation`); en Fuentes y Sistema scrollea la tabla o el panel, nunca la página. Reglas de movimiento: ninguna animación en acciones de teclado ni de uso frecuente, transiciones de 200 ms o menos con `--ease-out`, `active:scale-[0.97]` en botones, nada de `transition: all`, hover solo con `@media (hover: hover)` y `prefers-reduced-motion` anula Shimmer y transiciones.

Sistema pinta cada pieza con estado en texto y color, latencia y última consulta. Fuentes ofrece tabla, filtro, detalle lateral y la cola de subida. El visor de citas fue panel lateral en pantallas grandes y hoja inferior en móvil hasta v0.11; desde v0.12 es un modal a pantalla completa (ver abajo).

## Citas, visor y avisos v0.12

- **Marcadores inline.** Botón numérico de ~18 px pegado a la frase (`citation-marker.tsx`), con `HoverCard` que muestra documento, ubicación y fragmento literal. Un carácter de unión de palabra evita que el marcador se quede solo al final de línea. Debajo, el desplegable «N fuentes». Sin segmentos válidos se degrada a las píldoras numeradas tras la respuesta.
- **Visor a pantalla completa.** `Dialog` con el lienzo (`features/viewer/page-canvas.tsx`) y un panel de detalle (derecha en escritorio, bajo la página en móvil). Zoom con rueda, pellizco, doble clic, botones y `+`, `-`, `0`; arrastre para mover; ←/→ cambian de cita y ↑/↓ de página del fragmento; Esc cierra. Ninguna de estas acciones de teclado se anima. La marca del fragmento es amarilla con `mix-blend-mode: multiply` sobre el papel blanco y es igual en claro y oscuro (la página siempre es blanca). El visor dice en un aviso lo que no puede hacer (fragmento no localizado, PDF ausente, factura con OCR sin posiciones).
- **Añadir fuentes.** Botón primario en la barra lateral, en el estado vacío del chat y en Fuentes; abre un `Dialog` con la zona de suelta resaltada al arrastrar. Al elegir o soltar archivos el diálogo se cierra.
- **Avisos.** Sonner (shadcn, sobre el `ThemeProvider` propio, sin `next-themes`) con un único aviso persistente de subidas: una fila por archivo con su estado real, reintento en los errores recuperables, «Ver en Fuentes» y cierre cuando todo ha terminado. Se oculta solo a los 12 s si todo fue bien. Los demás avisos puntuales usan `toast()` de Sonner (el antiguo `ToastProvider` se retiró).
- `Kbd` (`components/ui/kbd.tsx`) para las pistas de teclado.

## Aclaración y vista previa v0.13.1

- **Tarjeta de aclaración** (`components/chat/clarification.tsx`). Pregunta corta como título y las candidatas como `Item` de shadcn renderizado como botón: número y fecha arriba, «De X para Y» debajo y el total a la derecha, solo los datos que existen. El nombre accesible de cada botón dice factura, partes, fecha y total. Tab llega a cada botón; ↑/↓, Inicio y Fin mueven el foco sin animación. Hover solo con `@media (hover: hover)` y `active:scale-[0.985]`. Sin iconos decorativos. Con más de 5 candidatas lo dice y pide acotar.
- **Vista previa de cita.** El panel se centra en el marcador, deja 12 px a los bordes del hilo (v0.13.2: antes, de la ventana) y se oculta si el marcador sale del hilo. Nace desde el marcador (`--transform-origin`). Dentro de un hilo, su límite de colisión es el elemento de scroll (`useConversationScrollArea`): se abre hacia arriba si abajo no cabe y se ciñe al hilo, con scroll interno, si no cabe en ninguna dirección, de modo que nunca cubre el composer.

## Respuestas con datos

Desde v0.14.0, Artifact agrupa una ficha `dl` o una tabla de facturas derivadas del servicio. Reutiliza Button y Tooltip de Base UI, Table y Skeleton de shadcn, y Message y Suggestion de AI Elements. El contrato está en [ADR-014](decisions-log.md#adr-014-bloques-de-respuesta-derivados-de-evidencia-2026-11-01).

Cada valor presente tiene una cita junto a él. Las sumas muestran los marcadores de los operandos. La ficha general incluye emisor, cliente, número, fecha y total; una pregunta por un campo conserva solo ese campo. Un guion con nombre accesible "sin dato" representa ausencia, nunca cero. Los importes y fechas usan cifras tabulares y no parten el símbolo; las columnas de importes se alinean a la derecha. La tabla se desplaza dentro del hilo en móvil.

El Markdown sigue siendo la alternativa completa para clientes sin bloques o ante una versión o estructura que no se pueda validar. El realce de cifras en Markdown solo envuelve texto literal, sin cambiar valores ni añadir campos. Omite código y enlaces.

La copia de respuesta conserva Markdown y fuentes. La copia de tabla usa TSV con igual número de columnas y conserva notas de revisión o truncamiento. Alt+C copia la respuesta, Alt+T la tabla y Alt+1 a Alt+3 envían sugerencias; actúan fuera de campos editables y del visor. La ayuda lista estos atajos.

Mientras llega contenido se muestra Skeleton, oculto para lectores de pantalla, junto al estado accesible. El texto provisional entra con fade de 140 ms y sigue marcado como pendiente de verificación. Con `prefers-reduced-motion`, no se anima el streaming, no hay retardos CSS ni scroll suave de seguimiento. El envío por teclado lleva al final de forma instantánea.

Auditoría de componentes y decisiones de copy en [revisión v0.14.0](reviews/respuestas-enriquecidas-v0.14.0.md). Capturas sintéticas antes/después en [comparación](../evidence/comparison-v0.13.3-v0.14.0/README.md).
