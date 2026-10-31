// Capturas de la aclaración de facturas y de la vista previa de una cita, contra un stack con las fuentes de evidence/fixtures indexadas.
// Uso desde apps/web: BASE=http://127.0.0.1:3000 node e2e/capture-aclaracion.mjs
// Imprime cuántos píxeles invade la tarjeta al composer (0 = no lo toca).
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños), DOC_QUESTION (pregunta de documento con cita).
import { chromium } from "@playwright/test"

const BASE = process.env.BASE ?? "http://127.0.0.1:3000"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const DOC_QUESTION = process.env.DOC_QUESTION ?? "¿Qué alcance tiene el sensor SX-20?"
const only = process.env.ONLY?.split(",")
const sizes = [["1440x900", { width: 1440, height: 900 }], ["1280x720", { width: 1280, height: 720 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "industrial-dark", "neutral-light", "neutral-dark"]
const final = '[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"], [data-testid="assistant-message"][data-kind="clarification"], [data-testid="assistant-message"][data-kind="failed"]'

const browser = await chromium.launch()
for (const [name, viewport] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
    await ctx.addInitScript(([t, m]) => { localStorage.setItem("doc-assistant.theme", t); localStorage.setItem("doc-assistant.mode", m) }, [theme, mode])
    const page = await ctx.newPage()
    const shot = (scene) => page.screenshot({ path: `${OUT}/${scene}-${name}-${th}.png` })
    const ask = async (question, index) => {
      await page.getByLabel("Pregunta", { exact: true }).fill(question)
      await page.keyboard.press("Enter")
      await page.locator(final).nth(index).waitFor({ timeout: 120000 })
      await page.waitForTimeout(600)
    }

    await page.goto(BASE + "/")
    await ask("¿Cuál es el importe total de la factura?", 0)
    const candidates = page.getByTestId("clarification-candidate")
    if (await candidates.count()) {
      await candidates.first().focus()
      await shot("aclaracion")
      await candidates.first().click()
      await page.locator(final).nth(1).waitFor({ timeout: 120000 })
      await page.waitForTimeout(800)
      await shot("aclaracion-respuesta")
    } else console.warn(`sin candidatas en ${name}-${th}`)

    await ask(DOC_QUESTION, 2)
    const marker = page.getByTestId("citation-marker-1").last()
    if (await marker.count()) {
      await marker.scrollIntoViewIfNeeded()
      if (viewport.width >= 768) await marker.hover()
      else await marker.focus()
      await page.waitForTimeout(600)
      await shot("cita-vista-previa")
      const overlap = await page.evaluate(() => {
        const card = document.querySelector('[data-slot="hover-card-content"]')?.getBoundingClientRect()
        const composer = document.querySelector('[data-testid="composer"]')?.getBoundingClientRect()
        return card && composer ? Math.max(0, Math.round(card.bottom - composer.top)) : null
      })
      console.log(`${name}-${th}: la tarjeta invade el composer ${overlap} px`)
    } else console.warn(`sin marcador en ${name}-${th}`)
    await ctx.close()
  }
}
await browser.close()
