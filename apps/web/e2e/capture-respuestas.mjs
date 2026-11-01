// Capturas sintéticas (sin modelos) con el backend simulado de e2e/mocks.ts.
// Uso desde apps/web, con la web en marcha (pnpm exec next start --port 3100): BASE=http://127.0.0.1:3100 node e2e/capture-respuestas.mjs
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños), SCENES (rechazo,factura,datos-clave,tabla),
// LEGACY=1 (respuestas sin bloques ni sugerencias: lo que enviaba el servicio hasta v0.13.3, para capturar el «antes»),
// PREFIX (antepone una etiqueta al nombre del archivo).
import { chromium } from "@playwright/test"

import {
  answerEvents,
  ask,
  KEY_DATA_BLOCK,
  KEY_DATA_CITATIONS,
  KEY_DATA_FOLLOW_UPS,
  KEY_DATA_SEGMENTS,
  KEY_DATA_TEXT,
  mockBackend,
  refusalEvents,
  sse,
  step,
  TABLE_BLOCK,
  TABLE_CITATIONS,
  TABLE_SEGMENTS,
  TABLE_TEXT,
} from "./mocks.ts"

const BASE = process.env.BASE ?? "http://127.0.0.1:3100"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const LEGACY = process.env.LEGACY === "1"
const PREFIX = process.env.PREFIX ? `${process.env.PREFIX}-` : ""
const only = process.env.ONLY?.split(",")
const scenes = process.env.SCENES?.split(",") ?? ["rechazo", "factura", "datos-clave", "tabla"]
const sizes = [["1440x900", { width: 1440, height: 900 }], ["1280x720", { width: 1280, height: 720 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "industrial-dark", "neutral-light", "neutral-dark"]

const NO_INFO = "No dispongo de esa información en los documentos"
const INVOICE_CITATION = {
  chunk_id: "F-2026-001:importe_total",
  quote: "537,94 €",
  doc: "F-2026-001",
  doc_id: "inv-f-2026-001",
  section: "importe_total",
  pages: [1],
  fragment: "537,94 €",
}
const INVOICE_TEXT = "- Factura F-2026-001: precio final: 537,94 €"
const route = [step("route", "running", "Analizando la pregunta"), step("route", "done", "Consulta de facturas", 0.01)]

function refusal() {
  const events = refusalEvents("")
  const suggestions = events.find(([name]) => name === "refusal")[1].suggestions
  return events.filter(([name]) => name !== "token").map(([name, data]) =>
    name === "refusal" || name === "done" ? [name, { ...data, answer: NO_INFO, reason: "llm_unanswerable", suggestions }] : [name, data]
  )
}

const invoice = () => [...route, ...answerEvents(INVOICE_TEXT, [INVOICE_CITATION], [{ text: INVOICE_TEXT, refs: [0] }])]

const keyData = () =>
  LEGACY
    ? [...route, ...answerEvents(KEY_DATA_TEXT, KEY_DATA_CITATIONS, KEY_DATA_SEGMENTS)]
    : [...route, ...answerEvents(KEY_DATA_TEXT, KEY_DATA_CITATIONS, KEY_DATA_SEGMENTS, { blocks: [KEY_DATA_BLOCK], follow_ups: KEY_DATA_FOLLOW_UPS })]

const table = () =>
  LEGACY
    ? [...route, ...answerEvents(TABLE_TEXT, TABLE_CITATIONS, TABLE_SEGMENTS)]
    : [...route, ...answerEvents(TABLE_TEXT, TABLE_CITATIONS, TABLE_SEGMENTS, { blocks: [TABLE_BLOCK] })]

const SCENES = {
  rechazo: ["chat-rechazo", "¿Cuál es el precio del robot TX-10?", refusal],
  factura: ["chat-factura", "¿Cuál es el precio final de la factura F-2026-001?", invoice],
  "datos-clave": ["chat-datos-clave", "¿Qué datos tiene la factura F-2026-001?", keyData],
  tabla: ["chat-tabla", "¿Qué facturas de Talleres Puig hay, con su fecha y su importe?", table],
}

const browser = await chromium.launch()
for (const [name, viewport] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    for (const scene of scenes) {
      const [file, question, events] = SCENES[scene]
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
      await context.addInitScript(([t, m]) => {
        localStorage.setItem("doc-assistant.theme", t)
        localStorage.setItem("doc-assistant.mode", m)
      }, [theme, mode])
      const page = await context.newPage()
      await mockBackend(page, { ask: (r) => r.fulfill({ contentType: "text/event-stream", body: sse(events()) }) })
      await page.goto(BASE + "/")
      await ask(page, question)
      await page.locator('[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"]').first().waitFor()
      await page.mouse.move(0, 0)
      await page.waitForTimeout(700)
      await page.screenshot({ path: `${OUT}/${PREFIX}${file}-${name}-${th}.png` })
      await context.close()
    }
  }
}
await browser.close()
