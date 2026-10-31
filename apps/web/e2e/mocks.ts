import fs from "node:fs"
import path from "node:path"

import type { Page, Route } from "@playwright/test"

import type { Source } from "../src/lib/api/types"

/** Synthetic datasheet page, generated for the repo. */
export const PAGE_PNG = fs.readFileSync(path.join(process.cwd(), "e2e", "fixtures", "page-acme-demo-ds.png"))

export const CITATION = {
  chunk_id: "chunk-acme-ds-2-1",
  quote: "Carga útil máxima: 12 kg",
  doc: "ACME-DEMO-DS",
  doc_id: "pdf-acme-demo-ds",
  section: "2.1",
  pages: [1],
  fragment: "[pdf-acme-demo-ds · Ficha GR-50 · 2.1 Capacidad] 2.1 Capacidad de carga útil. Carga útil máxima: 12 kg (ISO 9409-1). Momento máximo en brida: 45 N·m.",
}

export const SECOND_CITATION = {
  ...CITATION,
  chunk_id: "chunk-acme-ds-flange",
  quote: "ISO 9409-1-50-4-M6",
  fragment: "Interfaz brida: ISO 9409-1-50-4-M6. Grado de protección IP54.",
}

export const SOURCES: Source[] = [
  {
    id: "pdf-acme-demo-ds",
    kind: "pdf",
    name: "ACME-DEMO-DS",
    title: "Ficha técnica de la pinza GR-50",
    n_pages: 2,
    n_chunks: 4,
    sections: [{ section: "2.1", heading: "Capacidad", pages: [1] }],
    added_at: "2026-10-30T10:00:00+00:00",
    status: "indexed",
    status_detail: null,
    file: "documents/ACME-DEMO-DS.pdf",
  },
  {
    id: "pdf-scan",
    kind: "pdf",
    name: "escaneo-sin-texto",
    title: null,
    n_pages: 3,
    n_chunks: 0,
    sections: [],
    added_at: "2026-10-29T09:00:00+00:00",
    status: "no_text",
    status_detail: "PDF sin capa de texto (necesita OCR)",
    file: null,
  },
  {
    id: "inv-F-2026-001",
    kind: "invoice",
    name: "F-2026-001",
    title: null,
    n_pages: 1,
    n_chunks: 1,
    sections: [],
    added_at: "2026-10-31T08:00:00+00:00",
    status: "review",
    status_detail: "Revisar: el IVA no cuadra",
    file: "invoices/F-2026-001.png",
  },
]

export const INVOICE = {
  numero: "F-2026-001",
  fecha_emision: "2026-01-01",
  fecha_vencimiento: "2026-12-31",
  emisor: "María Soler García",
  nif_emisor: "59516774L",
  cliente: "Talleres Puig, S.A.",
  nif_cliente: "A49117963",
  base_imponible_total: "507.49",
  cuota_iva_total: "106.57",
  irpf_tipo: "15",
  irpf_importe: "76.12",
  recargo_total: null,
  importe_total: "537.94",
  iban: null,
  estado: "revisar",
  motivo: "El IVA no cuadra",
}

export type SseEvent = [event: string, data: Record<string, unknown>]

export function sse(events: SseEvent[]): string {
  return events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join("")
}

const step = (id: string, status: "running" | "done", label: string, elapsed_s?: number): SseEvent => [
  "step",
  { id, status, label, data: {}, elapsed_s: elapsed_s ?? null },
]

export type Segment = { text: string; refs: number[] }

export function answerEvents(
  text = "La carga útil máxima es de 12 kg.",
  citations = [CITATION],
  segments: Segment[] = []
): SseEvent[] {
  return [
    step("retrieve", "running", "Buscando fragmentos relevantes"),
    step("retrieve", "done", "4 fragmentos candidatos", 0.05),
    step("generate", "running", "Redactando la respuesta con los fragmentos"),
    ["token", { text }],
    step("generate", "done", "Respuesta redactada", 1.2),
    step("verify", "running", "Verificando citas contra los fragmentos"),
    step("verify", "done", "1 cita verificada", 0.01),
    ["citations", { citations }],
    [
      "done",
      { ok: true, answer: text, citations, segments, reason: "", suggestions: [], inline: segments.length > 0 ? "rules" : "none", timings: { total: 1.3 } },
    ],
  ]
}

export function refusalEvents(provisional = "Texto sin verificar"): SseEvent[] {
  const answer = "No dispongo de esa información en los documentos"
  return [
    step("generate", "running", "Redactando la respuesta con los fragmentos"),
    ["token", { text: provisional }],
    step("generate", "done", "Respuesta redactada", 0.8),
    step("verify", "running", "Verificando citas contra los fragmentos"),
    step("verify", "done", "Sin respaldo en las fuentes", 0.01),
    [
      "refusal",
      {
        answer,
        reason: "verify:numbers",
        retract: true,
        suggestions: [{ doc: "ACME-DEMO-DS", doc_id: "pdf-acme-demo-ds", section: "3", heading: "Dimensiones", pages: [1] }],
      },
    ],
    ["done", { ok: false, answer, citations: [], reason: "verify:numbers", suggestions: [], inline: "none", timings: { total: 0.9 } }],
  ]
}

export type Highlight = { page: number; found: boolean; reason: "ok" | "not_found" | "no_positions" | "no_file"; rects?: { x: number; y: number; w: number; h: number }[] }

export const FOUND: Highlight = { page: 1, found: true, reason: "ok", rects: [{ x: 0.12, y: 0.32, w: 0.5, h: 0.03 }] }

export type BackendOptions = {
  highlight?: (quote: string) => Highlight
  sources?: Source[]
  ask?: (route: Route, question: string) => Promise<void> | void
}

const HEALTH = {
  components: [
    { id: "ai", status: "ok", latency_ms: null, detail: "Responde" },
    { id: "llm", status: "ok", latency_ms: 3.1, detail: "127.0.0.1:8081" },
    { id: "embeddings", status: "ok", latency_ms: 2.2, detail: "127.0.0.1:8082" },
    { id: "reranker", status: "degraded", latency_ms: 40, detail: "cargando el modelo" },
    { id: "ocr", status: "unavailable", latency_ms: null, detail: "127.0.0.1:8084" },
    { id: "sqlite", status: "ok", latency_ms: 0.6, detail: "4 fragmentos" },
  ],
}

/** Mocks every route the UI reads. Later page.route calls in a test win over these. */
export async function mockBackend(page: Page, options: BackendOptions = {}) {
  let sources = options.sources ?? SOURCES
  const questions: string[] = []
  await page.route("**/api/sources", (route) => route.fulfill({ json: sources }))
  await page.route("**/api/sources/*/chunks", (route) =>
    route.fulfill({
      json: [
        { chunk_id: "c1", section: "2.1", pages: [1], text: "Carga útil máxima: 12 kg (ISO 9409-1)." },
        { chunk_id: "c2", section: "3", pages: [2], text: "Dimensiones: 120 x 80 x 45 mm." },
      ],
    })
  )
  await page.route("**/api/sources/*/pages/*/highlight*", (route) => {
    const quote = new URL(route.request().url()).searchParams.get("quote") ?? ""
    return route.fulfill({ json: options.highlight ? options.highlight(quote) : FOUND })
  })
  await page.route("**/api/sources/*/pages/*", (route) => route.fulfill({ contentType: "image/png", body: PAGE_PNG }))
  await page.route("**/api/sources/*", async (route) => {
    if (route.request().method() === "DELETE") {
      const id = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "")
      sources = sources.filter((item) => item.id !== id)
      await route.fulfill({ status: 204 })
      return
    }
    await route.fallback()
  })
  await page.route("**/api/invoices", (route) => route.fulfill({ json: [INVOICE] }))
  await page.route("**/api/invoices/*/image", (route) => route.fulfill({ contentType: "image/png", body: PAGE_PNG }))
  await page.route("**/api/health", (route) => route.fulfill({ json: { status: "ok" } }))
  await page.route("**/api/health/components", (route) => route.fulfill({ json: HEALTH }))
  await page.route("**/api/ask/stream", async (route) => {
    const body = route.request().postDataJSON() as { question: string }
    questions.push(body.question)
    if (options.ask) return options.ask(route, body.question)
    await route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents()) })
  })
  return { questions }
}

export const composer = (page: Page) => page.getByLabel("Pregunta", { exact: true })

export async function ask(page: Page, question: string) {
  await composer(page).fill(question)
  await composer(page).press("Enter")
}
