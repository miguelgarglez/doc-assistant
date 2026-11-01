// Capturas contra un stack real con material propio del usuario (el kit). NO escribir en el repo: OUT debe ser una carpeta externa.
// Uso desde apps/web: BASE=http://127.0.0.1:3170 OUT=/ruta/externa PREFIX=v0.13.3 QUESTIONS='{"valor":"¿...?"}' node e2e/capture-real.mjs
// Variables: THEMES (tema-modo separados por coma), ONLY (tamaños), PREFIX (etiqueta del nombre), FULL=1 (captura de página completa del hilo).
import { chromium } from "@playwright/test"

const BASE = process.env.BASE ?? "http://127.0.0.1:3170"
const OUT = process.env.OUT
if (!OUT || OUT.includes("/wt/")) throw new Error("OUT debe ser una carpeta fuera del repo")
const PREFIX = process.env.PREFIX ?? "real"
const QUESTIONS = JSON.parse(process.env.QUESTIONS ?? "{}")
const only = process.env.ONLY?.split(",")
const sizes = [["1440x900", { width: 1440, height: 900 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "neutral-dark"]
const final = '[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"], [data-testid="assistant-message"][data-kind="clarification"], [data-testid="assistant-message"][data-kind="failed"]'

const browser = await chromium.launch()
for (const [name, viewport] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    for (const [scene, question] of Object.entries(QUESTIONS)) {
      const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
      await ctx.addInitScript(([t, m]) => { localStorage.setItem("doc-assistant.theme", t); localStorage.setItem("doc-assistant.mode", m) }, [theme, mode])
      const page = await ctx.newPage()
      await page.goto(BASE + "/")
      await page.getByLabel("Pregunta", { exact: true }).fill(question)
      await page.keyboard.press("Enter")
      await page.locator(final).first().waitFor({ timeout: 180000 })
      await page.waitForTimeout(900)
      await page.screenshot({ path: `${OUT}/${PREFIX}-${scene}-${name}-${th}.png` })
      await ctx.close()
    }
  }
}
await browser.close()
