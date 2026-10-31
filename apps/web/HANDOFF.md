# apps/web — handoff

Scaffold Next.js (App Router) + TypeScript strict + Tailwind v4 + shadcn/ui (**Base UI**, no Radix) en `feat/web-scaffold`.

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
| cn | 0.5.1 |
| tw-animate-css | 1.4.0 |
| openapi-typescript | 7.13.0 |

## Capas

1. **Tokens** — variables CSS en `src/app/globals.css` (`:root` / `.dark` + `@theme inline`).
2. **Primitivos** — `src/components/ui/*` (shadcn sobre `@base-ui/react`).
3. **Dominio** — `src/components/domain/*` con datos tipados en `src/lib/domain/`.
4. **Página** — `src/app/page.tsx` monta los componentes de dominio con ejemplos.

## Comandos

Desde `apps/web`:

```bash
pnpm install
pnpm dev
pnpm lint
pnpm typecheck
pnpm build
pnpm gen:api
```

- `gen:api` lee `../../services/ai/openapi.json` y escribe `src/lib/api/schema.d.ts`.
- Proxy BFF: `src/app/api/[...path]/route.ts` → `AI_SERVICE_URL` (default `http://127.0.0.1:8000`). Ver `.env.example`.

## shadcn / Base UI

Inicializado con:

```bash
pnpm dlx shadcn@latest init --base base --preset nova --css-variables -y --no-monorepo
pnpm dlx shadcn@latest add card button badge alert separator scroll-area -y
```

Confirmación: `pnpm dlx shadcn@latest info` → `"base": "base"`, style `base-nova`. Docs: https://ui.shadcn.com/docs/cli (`-b, --base base|radix|aria`).

## Fuera de alcance

Sin Storybook. Sin lógica especulativa de upload/consulta real (UI de ejemplo). Sin push.
