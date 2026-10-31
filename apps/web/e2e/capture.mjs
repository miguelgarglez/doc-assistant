// Capturas reales: necesita el stack levantado (mise run start) con las fuentes de demostración indexadas.
// Uso desde apps/web: BASE=http://127.0.0.1:3000 node e2e/capture.mjs
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños), ROUTES.
import { chromium } from "@playwright/test"
const BASE = process.env.BASE ?? "http://127.0.0.1:3000"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const only = process.env.ONLY?.split(",")
const sizes = [["1440x900", { width: 1440, height: 900 }], ["1280x720", { width: 1280, height: 720 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "industrial-dark", "neutral-light", "neutral-dark"]
const browser = await chromium.launch()
for (const [name, vp] of sizes) {
  if (only && !only.includes(name)) continue
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
    await ctx.addInitScript(([t, m]) => { localStorage.setItem("doc-assistant.theme", t); localStorage.setItem("doc-assistant.mode", m) }, [theme, mode])
    const page = await ctx.newPage()
    const tag = `${name}-${th}`
    await page.goto(BASE + "/")
    await page.waitForTimeout(700)
    await page.screenshot({ path: `${OUT}/chat-vacio-${tag}.png` })
    for (const q of ["¿Qué alcance tiene el sensor SX-20?", "¿Qué temperatura de trabajo admite el sensor?"]) {
      await page.getByLabel("Pregunta", { exact: true }).fill(q)
      await page.keyboard.press("Enter")
      await page.waitForTimeout(600)
      await page.screenshot({ path: `${OUT}/chat-generando-${tag}.png` })
      await page.locator('[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"], [data-testid="assistant-message"][data-kind="failed"]').nth(q.includes("alcance") ? 0 : 1).waitFor({ timeout: 90000 }).catch(() => {})
      await page.waitForTimeout(500)
    }
    await page.screenshot({ path: `${OUT}/chat-respuestas-${tag}.png` })
    const pill = page.getByTestId("citation-1").last()
    if (await pill.count()) {
      await pill.click()
      await page.waitForTimeout(900)
      await page.screenshot({ path: `${OUT}/chat-visor-${tag}.png` })
    }
    // Rechazo con diseño propio: pregunta sin respaldo en las fuentes (conversación nueva).
    await page.goto(BASE + "/")
    await page.getByLabel("Pregunta", { exact: true }).fill("¿Cuál es el precio del robot TX-10?")
    await page.keyboard.press("Enter")
    await page.locator('[data-testid="assistant-message"][data-kind="refusal"]').first().waitFor({ timeout: 90000 }).catch(() => {})
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/chat-rechazo-${tag}.png` })
    for (const route of (process.env.ROUTES ?? "fuentes,sistema,ajustes").split(",").filter(Boolean)) {
      await page.goto(BASE + "/" + route)
      await page.waitForTimeout(1200)
      await page.screenshot({ path: `${OUT}/${route}-${tag}.png` })
    }
    await ctx.close()
  }
}
await browser.close()
