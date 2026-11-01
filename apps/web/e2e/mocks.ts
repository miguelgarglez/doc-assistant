import fs from "node:fs"
import path from "node:path"

import type { Page, Route } from "@playwright/test"

import type { Source } from "../src/lib/api/types"
import type { Block, Citation, Clarification, FollowUp, KeyDataBlock, TableBlock } from "../src/lib/chat/types"

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

export const step = (id: string, status: "running" | "done", label: string, elapsed_s?: number): SseEvent => [
  "step",
  { id, status, label, data: {}, elapsed_s: elapsed_s ?? null },
]

export type Segment = { text: string; refs: number[] }

export type Extras = { blocks?: Block[]; follow_ups?: FollowUp[] }

export function answerEvents(
  text = "La carga útil máxima es de 12 kg.",
  citations: Citation[] = [CITATION],
  segments: Segment[] = [],
  extras: Extras = {}
): SseEvent[] {
  const blocks = extras.blocks ?? []
  const follow_ups = extras.follow_ups ?? []
  return [
    step("retrieve", "running", "Buscando fragmentos relevantes"),
    step("retrieve", "done", "4 fragmentos candidatos", 0.05),
    step("generate", "running", "Redactando la respuesta con los fragmentos"),
    ["token", { text }],
    step("generate", "done", "Respuesta redactada", 1.2),
    step("verify", "running", "Verificando citas contra los fragmentos"),
    step("verify", "done", "1 cita verificada", 0.01),
    ["citations", { citations }],
    ...(blocks.length > 0 || follow_ups.length > 0 ? [["blocks", { blocks_version: 1, blocks, follow_ups }] as SseEvent] : []),
    [
      "done",
      {
        ok: true,
        answer: text,
        citations,
        segments,
        blocks_version: 1,
        blocks,
        follow_ups,
        reason: "",
        suggestions: [],
        inline: segments.length > 0 ? "rules" : "none",
        timings: { total: 1.3 },
        request_id: "request-demo",
      },
    ],
  ]
}

const invoiceCitation = (numero: string, campo: string, text: string): Citation => ({
  chunk_id: `${numero}:${campo}`,
  quote: text,
  doc: numero,
  doc_id: `inv-${numero.toLowerCase()}`,
  section: campo,
  pages: [1],
  fragment: text,
})

/** Synthetic invoice data for the structured blocks: every cell's text equals its citation's fragment. */
export const KEY_DATA_CITATIONS: Citation[] = [
  invoiceCitation("F-2026-001", "emisor", "María Soler García"),
  invoiceCitation("F-2026-001", "cliente", "Talleres Puig, S.A."),
  invoiceCitation("F-2026-001", "numero", "F-2026-001"),
  invoiceCitation("F-2026-001", "fecha_emision", "2026-01-01"),
  invoiceCitation("F-2026-001", "importe_total", "537,94 €"),
]

export const KEY_DATA_BLOCK: KeyDataBlock = {
  type: "key_data",
  title: "Datos clave",
  doc_id: "inv-f-2026-001",
  note: "Pendiente de revisión: F-2026-001",
  items: [
    { field: "emisor", label: "emisor", text: "María Soler García", kind: "text", cite: 0 },
    { field: "cliente", label: "cliente", text: "Talleres Puig, S.A.", kind: "text", cite: 1 },
    { field: "numero", label: "número", text: "F-2026-001", kind: "id", cite: 2 },
    { field: "fecha_emision", label: "fecha de emisión", text: "2026-01-01", kind: "date", cite: 3 },
    { field: "importe_total", label: "importe total", text: "537,94 €", kind: "amount", cite: 4 },
  ],
}

export const KEY_DATA_TEXT =
  "- Factura F-2026-001: importe total: 537,94 €; fecha de emisión: 2026-01-01; emisor: María Soler García; cliente: Talleres Puig, S.A."

export const KEY_DATA_SEGMENTS: Segment[] = [{ text: KEY_DATA_TEXT, refs: [4, 3, 0, 1] }]

export const KEY_DATA_FOLLOW_UPS: FollowUp[] = [
  { label: "Fecha de vencimiento", question: "¿Cuál es la fecha de vencimiento de la factura F-2026-001?" },
  { label: "Cuota de IVA", question: "¿Cuál es la cuota de IVA de la factura F-2026-001?" },
]

const ROWS = [
  ["F-2026-001", "2026-01-01", "537,94 €"],
  ["F-2026-002", "2026-02-14", "1.210,00 €"],
  ["F-2026-003", "2026-03-30", "99,50 €"],
] as const

export const TABLE_CITATIONS: Citation[] = ROWS.flatMap(([numero, fecha, total]) => [
  invoiceCitation(numero, "numero", numero),
  invoiceCitation(numero, "fecha_emision", fecha),
  invoiceCitation(numero, "importe_total", total),
])

export const TABLE_BLOCK: TableBlock = {
  type: "table",
  title: "Facturas de Talleres Puig, S.A.",
  columns: [
    { key: "numero", label: "Factura", kind: "id" },
    { key: "fecha_emision", label: "fecha de emisión", kind: "date" },
    { key: "importe_total", label: "importe total", kind: "amount" },
  ],
  rows: ROWS.map(([numero, fecha, total], i) => ({
    doc_id: `inv-${numero.toLowerCase()}`,
    question: `¿Qué datos tiene la factura ${numero}?`,
    cells: [
      { text: numero, kind: "id", cite: i * 3 },
      { text: fecha, kind: "date", cite: i * 3 + 1 },
      { text: total, kind: "amount", cite: i * 3 + 2 },
    ],
  })),
  summary: { label: "Total", text: "1.847,44 €", kind: "amount", operation: "sum", refs: [2, 5, 8] },
  note: null,
}

const TABLE_HEAD = "Facturas de Talleres Puig, S.A.:"
const TABLE_BULLETS = ROWS.map(([n, f, t]) => `- ${n} (fecha de emisión: ${f}; importe total: ${t})`)

export const TABLE_TEXT = `${TABLE_HEAD}\n\n${TABLE_BULLETS.join("\n")}`

export const TABLE_SEGMENTS: Segment[] = [
  { text: TABLE_HEAD, refs: [] },
  ...TABLE_BULLETS.map((bullet, i) => ({ text: `${i === 0 ? "\n\n" : "\n"}${bullet}`, refs: [i * 3, i * 3 + 1, i * 3 + 2] })),
]

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

export const CLARIFICATION: Clarification = {
  prompt: "¿De qué factura?",
  detail: null,
  total: 2,
  candidates: [
    {
      doc: "A-2026/014",
      doc_id: "inv-a-2026-014",
      emisor: "Suministros Aranda, S.L.",
      cliente: "Taller Norte, S.L.",
      fecha: "12/02/2026",
      total: "1.210,00 €",
      question: "¿Cuál es el importe total de la factura A-2026/014?",
    },
    {
      doc: "B-77",
      doc_id: "inv-b-77",
      emisor: "Clara Ibáñez Roca",
      cliente: null,
      fecha: null,
      total: null,
      question: "¿Cuál es el importe total de la factura B-77?",
    },
  ],
}

/** An ambiguous invoice question: the `clarification` event, then `done` with the same data. */
export function clarificationEvents(clarification = CLARIFICATION): SseEvent[] {
  const answer = `${clarification.prompt} ¿Te refieres a alguna de estas?`
  return [
    step("route", "running", "Analizando la pregunta"),
    step("route", "done", "Pregunta sobre documentos", 0.01),
    step("invoices", "running", "Comprobando si es una consulta de facturas"),
    step("invoices", "done", "Consulta de facturas", 1.1),
    ["clarification", { reason: "invoice:aclaracion", clarification }],
    ["done", { ok: false, answer, citations: [], reason: "invoice:aclaracion", suggestions: [], inline: "none", clarification, timings: { total: 1.2 } }],
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
  await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: false } }))
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
