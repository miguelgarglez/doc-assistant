// Captura sintética (sin modelos) de la vista previa de una cita al final de un hilo largo, con el backend simulado de e2e/mocks.ts.
// Uso desde apps/web, con la web en marcha (pnpm exec next start): BASE=http://127.0.0.1:3100 node e2e/capture-cita-final.mjs
// Imprime cuántos píxeles invade la tarjeta al composer (0 = no lo toca).
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños).
import { chromium } from "@playwright/test"

import { answerEvents, ask, CITATION, mockBackend, SECOND_CITATION, sse } from "./mocks.ts"

const BASE = process.env.BASE ?? "http://127.0.0.1:3100"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const only = process.env.ONLY?.split(",")
const sizes = [["1440x900", { width: 1440, height: 900 }], ["1280x720", { width: 1280, height: 720 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "industrial-dark", "neutral-light", "neutral-dark"]

const TEXT = "La carga útil máxima es de 12 kg. La interfaz de brida es ISO 9409-1-50-4-M6."
const SEGMENTS = [
  { text: "La carga útil máxima es de 12 kg.", refs: [0] },
  { text: " La interfaz de brida es ISO 9409-1-50-4-M6.", refs: [1] },
]
const LONG = {
  ...SECOND_CITATION,
  quote: "Carga útil máxima: 12 kg, medida con el centro de gravedad a 40 mm de la brida, a velocidad nominal y con la herramienta montada en posición vertical.",
}
const QUESTIONS = [
  "¿Cuál es la carga útil máxima?",
  "¿Qué brida monta la pinza?",
  "¿Y el grado de protección?",
  "¿Cuánto pesa?",
  "¿Qué par de apriete lleva?",
  "¿Cuál es la carga útil con la herramienta montada?",
]

const browser = await chromium.launch()
for (const [name, viewport] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    const context = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
    await context.addInitScript(([t, m]) => {
      localStorage.setItem("doc-assistant.theme", t)
      localStorage.setItem("doc-assistant.mode", m)
    }, [theme, mode])
    const page = await context.newPage()
    await mockBackend(page, {
      ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(TEXT, [CITATION, LONG], SEGMENTS)) }),
    })
    await page.goto(BASE + "/")
    for (const [index, question] of QUESTIONS.entries()) {
      await ask(page, question)
      await page.locator('[data-testid="assistant-message"][data-kind="answer"]').nth(index).waitFor()
    }
    await page.waitForTimeout(900)
    const marker = page.getByTestId("citation-marker-2").last()
    const card = page.locator('[data-slot="hover-card-content"]')
    for (let attempt = 0; attempt < 5 && !(await card.isVisible()); attempt++) {
      await page.mouse.move(2, 2)
      await page.waitForTimeout(300)
      if (viewport.width >= 768) await marker.hover()
      else await marker.focus()
      await card.waitFor({ timeout: 2000 }).catch(() => undefined)
    }
    await card.waitFor({ timeout: 2000 })
    await page.waitForTimeout(600)
    const overlap = await page.evaluate(() => {
      const card = document.querySelector('[data-slot="hover-card-content"]')?.getBoundingClientRect()
      const composer = document.querySelector('[data-testid="composer"]')?.getBoundingClientRect()
      return card && composer ? Math.max(0, Math.round(card.bottom - composer.top)) : null
    })
    console.log(`${name}-${th}: la tarjeta invade el composer ${overlap} px`)
    await page.screenshot({ path: `${OUT}/cita-final-hilo-${name}-${th}.png` })
    await context.close()
  }
}
await browser.close()
