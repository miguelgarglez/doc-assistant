// Capturas reales: necesita el stack levantado (mise run start) con las fuentes de demostración de evidence/fixtures indexadas.
// Uso desde apps/web: BASE=http://127.0.0.1:3000 node e2e/capture.mjs
// Variables: OUT (carpeta), THEMES (tema-modo separados por coma), ONLY (tamaños), ROUTES.
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

import { chromium } from "@playwright/test"

const BASE = process.env.BASE ?? "http://127.0.0.1:3000"
const OUT = process.env.OUT ?? "../../evidence/screenshots"
const FIXTURES = path.resolve(process.env.FIXTURES ?? "../../evidence/fixtures")
const only = process.env.ONLY?.split(",")
const sizes = [["1440x900", { width: 1440, height: 900 }], ["1280x720", { width: 1280, height: 720 }], ["390x844", { width: 390, height: 844 }]]
const themes = process.env.THEMES?.split(",") ?? ["industrial-light", "industrial-dark", "neutral-light", "neutral-dark"]
const notes = path.join(os.tmpdir(), "notas.txt")
const extraPdf = process.env.UPLOAD_PDF
fs.writeFileSync(notes, "apuntes sueltos")

const answerSelector =
  '[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"], [data-testid="assistant-message"][data-kind="failed"]'

const browser = await chromium.launch()
for (const [name, vp] of sizes) {
  if (only && !only.includes(name)) continue
  const narrow = vp.width < 768
  for (const th of themes) {
    const [theme, mode] = th.split("-")
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, locale: "es-ES", colorScheme: mode })
    await ctx.addInitScript(([t, m]) => { localStorage.setItem("doc-assistant.theme", t); localStorage.setItem("doc-assistant.mode", m) }, [theme, mode])
    const page = await ctx.newPage()
    const tag = `${name}-${th}`
    const shot = (scene) => page.screenshot({ path: `${OUT}/${scene}-${tag}.png` })
    const ask = async (question, index) => {
      await page.getByLabel("Pregunta", { exact: true }).fill(question)
      await page.keyboard.press("Enter")
      await page.waitForTimeout(600)
      return page.locator(answerSelector).nth(index).waitFor({ timeout: 120000 }).catch(() => {})
    }
    const newChat = async () => {
      if (narrow) await page.getByRole("button", { name: "Abrir el menú" }).click()
      await page.getByTestId("new-conversation").click()
      await page.waitForTimeout(300)
    }
    const openAddSources = async () => {
      if (narrow) await page.getByRole("button", { name: "Abrir el menú" }).click()
      await page.getByTestId("add-sources").click()
      await page.getByTestId("dropzone").waitFor()
    }

    await page.goto(BASE + "/")
    await page.waitForTimeout(700)
    await shot("chat-vacio")

    await page.getByLabel("Pregunta", { exact: true }).fill("¿Qué alcance tiene el sensor SX-20?")
    await page.keyboard.press("Enter")
    await page.waitForTimeout(600)
    await shot("chat-generando")
    await page.locator(answerSelector).nth(0).waitFor({ timeout: 120000 }).catch(() => {})
    await page.waitForTimeout(500)
    await ask("¿Qué temperatura de trabajo admite el sensor?", 1)
    await page.waitForTimeout(500)
    await shot("chat-respuestas")

    const marker = page.getByTestId("citation-marker-1").last()
    if (await marker.count()) {
      if (!narrow) {
        await marker.hover()
        await page.waitForTimeout(500)
        await shot("chat-cita")
        await page.mouse.move(5, 5)
      }
      await marker.click()
      await page.getByTestId("page-canvas").waitFor()
      await page.waitForTimeout(1600)
      await shot("chat-visor")
      await page.keyboard.press("Escape")
      await page.waitForTimeout(300)
    }

    // Respuestas de metadatos: lista de documentos con una cita por elemento.
    await newChat()
    await ask("¿Qué documentos hay?", 0)
    await page.waitForTimeout(500)
    await shot("chat-meta")

    // Factura: el visor enseña el campo extraído y dice por qué no hay resaltado.
    await newChat()
    await ask("¿Cuál es el importe total de la factura F-2026-001?", 0)
    await page.waitForTimeout(500)
    const invoiceMarker = page.getByTestId("citation-marker-1").first()
    if (await invoiceMarker.count()) {
      await invoiceMarker.click()
      await page.getByTestId("page-canvas").waitFor()
      await page.waitForTimeout(1500)
      await shot("chat-visor-factura")
      await page.keyboard.press("Escape")
    }

    // Rechazo con diseño propio: pregunta sin respaldo en las fuentes (conversación nueva).
    await newChat()
    await page.getByLabel("Pregunta", { exact: true }).fill("¿Cuál es el precio del robot TX-10?")
    await page.keyboard.press("Enter")
    await page.locator('[data-testid="assistant-message"][data-kind="refusal"]').first().waitFor({ timeout: 120000 }).catch(() => {})
    await page.waitForTimeout(500)
    await shot("chat-rechazo")

    // Añadir fuentes: el diálogo y, tras elegir archivos, el aviso con cada estado real.
    await newChat()
    const known = new Set((await (await page.request.get(BASE + "/api/sources")).json()).map((source) => source.id))
    await openAddSources()
    await page.waitForTimeout(400)
    await shot("anadir-fuentes")
    await page.getByTestId("sources-file-input").setInputFiles([
      path.join(FIXTURES, "invoices", process.env.UPLOAD_INVOICE ?? "factura_051.png"),
      ...(extraPdf ? [extraPdf] : []),
      notes,
    ])
    await page.getByTestId("upload-toast").waitFor()
    await page.waitForFunction(() => document.querySelector('[data-testid="upload-row"][data-status="processing"]'), null, { timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(2500)
    await shot("subida-aviso")
    await page.waitForFunction(
      () => Array.from(document.querySelectorAll('[data-testid="upload-row"]')).every((row) => ["done", "error"].includes(row.dataset.status)),
      null,
      { timeout: 180000 }
    ).catch(() => {})
    await page.getByTestId("upload-toast-close").click().catch(() => {})
    // Deja el índice como estaba para que la siguiente combinación vuelva a subir lo mismo.
    const uploaded = await (await page.request.get(BASE + "/api/sources")).json()
    for (const source of uploaded) {
      if (!known.has(source.id)) await page.request.delete(BASE + "/api/sources/" + source.id)
    }

    for (const route of (process.env.ROUTES ?? "fuentes,sistema,ajustes").split(",").filter(Boolean)) {
      await page.goto(BASE + "/" + route)
      await page.waitForTimeout(1200)
      await shot(route)
    }
    await ctx.close()
  }
}
await browser.close()
