# apps/web — handoff

Next.js (App Router) + TypeScript strict + Tailwind v4 + shadcn/ui (**Base UI**, no Radix). Cliente tipado `openapi-fetch` → BFF `/api` → `services/ai`. Página principal: **Doc Assistant** con pestañas Base UI **Consulta** / **Facturas**. Rama `feat/web-invoices`.

## Versiones instaladas

| Pieza | Versión |
| --- | --- |
| Node | 26.7.0 |
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
4. **Dominio** — `src/components/domain/*` reciben datos por props; hooks `use-ask`, `use-invoices`, `use-document-upload`.
5. **Página** — `src/app/page.tsx` monta pestañas Consulta (`AskWorkspace`) / Facturas (`InvoicesWorkspace`; lazy al activar la pestaña).

## Flujo ask (pestaña Consulta)

- `QuestionBox` → `api.POST("/ask")`.
- Estados: vacío (`idle`), skeleton de carga (`AskLoadingSkeleton`), `AskErrorNotice` con **Reintentar**, `RefusalNotice`, `AnswerCard` + `CitationChips`.
- Layout resultado: respuesta y fuente **lado a lado en `lg+`**, apilados en móvil.
- Cita activa → `SourceViewer`: página a escala, zoom clic, fragmento resaltado, anterior/siguiente.
- Al pie: `DocumentUploadPanel` → `POST /documents` (PDF); muestra `n_chunks` y «ya indexado» si `created=false`.

## Flujo facturas (pestaña Facturas)

- `UploadDropzone` (PNG/JPG) → `POST /invoices/upload` (multipart tipado). Skeleton al subir; error `{code,message}` con reintento.
- `InvoiceReviewCard` con `InvoiceUploadResponse`: badge `ok` / `revisar` + motivo; campos del `record` (null → `—  no encontrado`); flag `derivado`; evidencia OCR por campo (`<details>`); imagen `GET /invoices/{id}/image` con zoom. Importes es-ES desde Decimal-string (sin float).
- Lista compacta `GET /invoices`; clic abre la ficha (reutiliza la respuesta de upload en sesión si existe).

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
