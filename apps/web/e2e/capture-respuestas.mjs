// Capturas sintéticas (sin modelos) con el backend simulado de e2e/mocks.ts.
// Uso desde apps/web, con la web en marcha (pnpm exec next start --port 3100): BASE=http://127.0.0.1:3100 node e2e/capture-respuestas.mjs
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños), SCENES (rechazo,factura).
import { chromium } from "@playwright/test"

import { answerEvents, ask, mockBackend, refusalEvents, sse, step } from "./mocks.ts"

const BASE = process.env.BASE ?? "http://127.0.0.1:3100"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const only = process.env.ONLY?.split(",")
const scenes = process.env.SCENES?.split(",") ?? ["rechazo", "factura"]
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

function refusal() {
  const events = refusalEvents("")
  const suggestions = events.find(([name]) => name === "refusal")[1].suggestions
  return events.filter(([name]) => name !== "token").map(([name, data]) =>
    name === "refusal" || name === "done" ? [name, { ...data, answer: NO_INFO, reason: "llm_unanswerable", suggestions }] : [name, data]
  )
}

function invoice() {
  const events = answerEvents(INVOICE_TEXT, [INVOICE_CITATION], [{ text: INVOICE_TEXT, refs: [0] }])
  return [step("route", "running", "Analizando la pregunta"), step("route", "done", "Consulta de facturas", 0.01), ...events]
}

const QUESTIONS = {
  rechazo: ["¿Cuál es el precio del robot TX-10?", refusal],
  factura: ["¿Cuál es el precio final de la factura F-2026-001?", invoice],
}

const browser = await chromium.launch()
for (const [name, viewport] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    for (const scene of scenes) {
      const [question, events] = QUESTIONS[scene]
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
      await context.addInitScript(([t, m]) => {
        localStorage.setItem("doc-assistant.theme", t)
        localStorage.setItem("doc-assistant.mode", m)
      }, [theme, mode])
      const page = await context.newPage()
      await mockBackend(page, { ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(events()) }) })
      await page.goto(BASE + "/")
      await ask(page, question)
      await page.locator('[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"]').first().waitFor()
      await page.waitForTimeout(700)
      await page.screenshot({ path: `${OUT}/${scene === "rechazo" ? "chat-rechazo" : "chat-factura"}-${name}-${th}.png` })
      await context.close()
    }
  }
}
await browser.close()
