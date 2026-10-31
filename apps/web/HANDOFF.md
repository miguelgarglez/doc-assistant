# apps/web — handoff

Next.js (App Router) + TypeScript strict + Tailwind v4 + shadcn/ui (**Base UI**, no Radix). Cliente tipado `openapi-fetch` → BFF `/api` → `services/ai`. Página principal: **Doc Assistant** (documentación de robótica industrial local, no fiscal). Rama `feat/web-polish`.

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
2. **Primitivos** — `src/components/ui/*` (shadcn sobre `@base-ui/react`), incl. `skeleton`.
3. **API tipada** — `src/lib/api/schema.d.ts` (generado) + `client.ts` (`baseUrl: "/api"`). Tipos de respuesta desde el schema; sin DTOs a mano.
4. **Dominio** — `src/components/domain/*` reciben datos por props; estado de consulta en `src/hooks/use-ask.ts`.
5. **Página** — `src/app/page.tsx` monta `AskWorkspace` (pregunta → `/ask` → respuesta / rechazo / error + `SourceViewer`).

## Flujo ask

- `QuestionBox` → `api.POST("/ask")`.
- Estados: vacío (`idle`), skeleton de carga (`AskLoadingSkeleton`), `AskErrorNotice` con **Reintentar**, `RefusalNotice` (icono + razón + aviso de no inventar), `AnswerCard` + `CitationChips`.
- Layout resultado: respuesta y fuente **lado a lado en `lg+`**, apilados en móvil.
- Cita activa → `SourceViewer`: página completa a escala, **clic para ampliar/reducir**, fragmento resaltado debajo, **anterior/siguiente** si hay varias citas. Metadatos `doc` / sección / página / `chunk_id` en `font-mono`.
- Accesible: labels, `aria-pressed` en citas y zoom, región con focus al abrir fuente, `role="status"` / `aria-live`.

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
- `e2e` hace `pnpm build` y Playwright (Chromium). Intercepta `/api/*` con fixtures técnicas (`ACME-DEMO-DS`, §2.1, p. 1); imagen `e2e/fixtures/page-acme-demo-ds.png`. Capturas deterministas en `../../evidence/screenshots/`:
  - desktop 1280×800: `ask-answer-with-source.png`, `ask-refusal.png`, `ask-error.png`
  - móvil 390×844: `*-mobile.png` equivalentes
  Fuente fija en captura para determinismo.

## shadcn / Base UI

Inicializado con:

```bash
pnpm dlx shadcn@latest init --base base --preset nova --css-variables -y --no-monorepo
pnpm dlx shadcn@latest add card button badge alert separator scroll-area textarea label skeleton -y
```

Tras `add`, sustituir imports `from "cn"` por `@/lib/utils` (ADR-005). Confirmación: `pnpm dlx shadcn@latest info` → `"base": "base"`, style `base-nova`.

## Fuera de alcance

Sin Storybook. Sin upload/ingest/invoices en la UI de esta fase. Sin push. No editar `services/ai/openapi.json`.
