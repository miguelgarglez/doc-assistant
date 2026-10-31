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

Sistema pinta cada pieza con estado en texto y color, latencia y última consulta. Fuentes ofrece tabla, filtro, detalle lateral y la cola de subida. El visor de citas es panel lateral en pantallas grandes y hoja inferior en móvil.
