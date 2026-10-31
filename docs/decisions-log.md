# Registro de decisiones (ADR cortos)

## ADR-001 Monorepo con dos servicios (2026-10-31)
- Contexto: el núcleo (LLM, recuperación, OCR, SQLite) exige Python; la UI se evalúa y Miguel domina TS.
- Decisión: `services/ai` (FastAPI) + `apps/web` (Next.js, BFF proxy fino). Contrato OpenAPI como fuente de verdad.
- Alternativas: solo Python + HTMX; SPA estática servida por FastAPI; Gradio/Streamlit.
- Consecuencias: Node en runtime; se mitiga con `make dev` único. Confianza: media.

## ADR-002 shadcn/ui sobre Base UI (2026-10-31)
- Decisión de Miguel (t172). Tokens CSS → primitivos → componentes de dominio. Sin Storybook.
