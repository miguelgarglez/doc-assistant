# apps/web — handoff

Next.js (App Router) + TypeScript strict + Tailwind v4 + shadcn/ui (**Base UI**, no Radix). Cliente tipado `openapi-fetch` → BFF `/api` → `services/ai`. La aplicación agrupa chat, fuentes, subidas, historial, visor y sistema en `src/features`.

## Versiones instaladas

| Pieza | Versión |
| --- | --- |
| Node | 24.22.2 |
| pnpm | 10.21.0 |
| next | 16.4.3 |
| react / react-dom | 19.3.0 |
| typescript | 5.9.3 |
| tailwindcss | 4.3.3 |
| eslint / eslint-config-next | 9.39.5 / 16.4.3 |
| @base-ui/react | 1.9.0 |
| shadcn (CLI/pkg) | 4.23.0 |
| style preset | `base-nova` (`components.json` → `base: base`) |
| lucide-react | 1.66.0 |
| class-variance-authority | 0.7.1 |
| clsx + tailwind-merge | local `cn` en `src/lib/utils.ts` (ADR-005) |
| tw-animate-css | 1.4.0 |
| openapi-typescript | 7.13.0 |
| openapi-fetch | 0.17.0 |
| @playwright/test | 1.64.1 (solo Chromium) |
| tipografía | Geist Sans + Geist Mono vía `next/font` (`--font-sans` / `--font-mono`) |

## Capas

1. **Tokens** — variables CSS en `src/app/globals.css` (`:root` / `.dark` + `@theme inline`). Incluye `--highlight` para citas. Sin colores sueltos en componentes.
2. **Primitivos** — `src/components/ui/*` (shadcn sobre `@base-ui/react`), incl. `skeleton` y `tabs`.
3. **API tipada** — `src/lib/api/schema.d.ts` (generado) + `client.ts` (`baseUrl: "/api"`) + `upload.ts` (multipart FormData). Tipos desde el schema; sin DTOs a mano.
4. **Features** — `src/features/*` agrupa los componentes, hooks y estado de cada función. Cada `index.ts` es la entrada pública para otras features.
5. **Aplicación** — `src/app/*` contiene rutas, layout, proveedores y el proxy fino.

## Flujo de consulta

- `ChatProvider` usa `AskTransport` para consumir `POST /ask/stream`. Si el servicio no ofrece streaming, usa `POST /ask`.
- `ChatView` compone el estado vacío, el hilo y `Composer`. Los mensajes del asistente muestran texto provisional, rechazo, aclaración, bloques de datos, citas y errores.
- Los marcadores de cita abren el visor con la página, el fragmento resaltado, zoom y navegación entre citas.
- `use-question-history` conserva preguntas de la sesión. El historial persistido vive en la feature `history`.

## Fuentes y subidas

- `AddSourcesDialog` acepta PDF, PNG y JPEG. `UploadsProvider` mantiene la cola, el progreso, los errores recuperables y los reintentos.
- Los PDF usan el endpoint de documentos y las imágenes usan la subida de facturas. El aviso persistente conserva el estado al navegar.
- `SourcesView` filtra, ordena y elimina fuentes. `SourceDetail` muestra fragmentos y páginas de documentos, o los campos y la imagen de una factura.

## Comandos

Desde `apps/web`:

```bash
pnpm install
pnpm dev
pnpm lint
pnpm typecheck
pnpm build
pnpm gen:api
pnpm e2e
```

- `gen:api` lee `../../services/ai/openapi.json` y escribe `src/lib/api/schema.d.ts`.
- Proxy BFF: `src/app/api/[...path]/route.ts` → `AI_SERVICE_URL` (default `http://127.0.0.1:8000`). Ver `.env.example`.
- `e2e` hace `pnpm build` y Playwright (Chromium). Intercepta `/api/*` con fixtures:
  - ask: técnicos (`ACME-DEMO-DS`); imagen `e2e/fixtures/page-acme-demo-ds.png`
  - invoices: `../../evidence/fixtures/invoices/factura_001.png` + JSON coherente; variante `revisar` con nulls
  - Capturas deterministas en `../../evidence/screenshots/` (espera `document.fonts.ready`; no fuerza fuentes):
    - desktop 1280×800 / móvil 390×844: `ask-*.png`, `invoice-ok.png`, `invoice-review.png` (+ `-mobile`)

## shadcn / Base UI

```bash
pnpm dlx shadcn@latest init --base base --preset nova --css-variables -y --no-monorepo
pnpm dlx shadcn@latest add card button badge alert separator scroll-area textarea label skeleton tabs -y
```

Tras `add`, sustituir imports `from "cn"` por `@/lib/utils` (ADR-005); no dejar la dependencia npm `cn`. Confirmación: `pnpm dlx shadcn@latest info` → `"base": "base"`, style `base-nova`.

## Fuera de alcance

Sin Storybook. Sin push. No editar `services/ai/openapi.json`.
