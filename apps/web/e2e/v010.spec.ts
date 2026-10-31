import path from "node:path"
import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { askAnswerWithCitation, PAGE_PNG } from "./fixtures"

test.use({ reducedMotion: "reduce" })
const source = { id: "pdf-demo", kind: "pdf", name: "Ficha demo", title: "Ficha demo", n_pages: 1, n_chunks: 1, sections: [{ section: "1", heading: "Datos", pages: [1] }], added_at: null, status: "indexed", status_detail: null, file: null }

test.beforeEach(async ({ page }) => {
  await page.route("**/api/invoices", (route) => route.fulfill({ json: [] }))
  await page.route("**/api/sources", (route) => route.fulfill({ json: [source] }))
  await page.route("**/api/sources/pdf-demo/chunks", (route) => route.fulfill({ json: [{ chunk_id: "c1", section: "1", pages: [1], text: "Contenido de ejemplo." }] }))
  await page.route("**/api/sources/**/pages/**", (route) => route.fulfill({ contentType: "image/png", body: PAGE_PNG }))
  await page.route("**/api/health/components", (route) => route.fulfill({ status: 404 }))
})

test("stream provisional, respuesta final, hilo y recorrido", async ({ page }) => {
  await page.route("**/api/ask/stream", (route) => route.fulfill({ contentType: "text/event-stream", body: [
    'event: step\ndata: {"id":"retrieve","status":"running","label":"Buscando fragmentos"}\n\n',
    'event: step\ndata: {"id":"retrieve","status":"done","label":"Fragmentos encontrados"}\n\n',
    'event: token\ndata: {"text":"Texto provisional"}\n\n',
    `event: done\ndata: ${JSON.stringify(askAnswerWithCitation)}\n\n`,
  ].join("") }))
  await page.goto("/")
  await page.getByLabel("Pregunta").fill("Primera pregunta")
  await page.getByRole("button", { name: "Consultar" }).click()
  await expect(page.getByTestId("answer-card")).toBeVisible()
  await page.getByLabel("Pregunta").fill("Segunda pregunta")
  await page.getByRole("button", { name: "Consultar" }).click()
  await expect(page.getByTestId("answer-card")).toHaveCount(2)
  await page.getByRole("link", { name: "Sistema", exact: true }).click()
  await expect(page.getByRole("listitem").filter({ hasText: "Fragmentos encontrados" })).toBeVisible()
  await page.getByRole("button", { name: "Reproducir" }).click()
  await expect(page.getByText("Buscando fragmentos", { exact: false })).toBeVisible()
})

test("fuente muestra fragmentos y página", async ({ page }) => {
  await page.goto("/fuentes")
  await page.getByRole("button", { name: /Ficha demo/ }).click()
  await page.getByText("Fragmento 1 · p. 1").click()
  await expect(page.getByText("Contenido de ejemplo.")).toBeVisible()
  await expect(page.getByAltText("Página 1 de Ficha demo")).toBeVisible()
})

test("un rechazo retira el texto provisional", async ({ page }) => {
  await page.route("**/api/ask/stream", (route) => route.fulfill({ contentType: "text/event-stream", body: [
    'event: token\ndata: {"text":"Texto sin verificar"}\n\n',
    'event: refusal\ndata: {"answer":"No hay evidencia suficiente","reason":"verify","retract":true,"suggestions":[]}\n\n',
    'event: done\ndata: {"ok":false,"answer":"No hay evidencia suficiente","reason":"verify","citations":[],"suggestions":[],"timings":{}}\n\n',
  ].join("") }))
  await page.goto("/")
  await page.getByLabel("Pregunta").fill("Pregunta")
  await page.getByRole("button", { name: "Consultar" }).click()
  await expect(page.getByText("No hay evidencia suficiente")).toBeVisible()
  await expect(page.getByText("Texto sin verificar")).toHaveCount(0)
})

for (const theme of ["industrial", "neutral"] as const) {
  for (const dark of [false, true]) {
    for (const route of ["/", "/fuentes", "/ajustes", "/sistema"]) {
      test(`axe ${route} ${theme} ${dark ? "oscuro" : "claro"}`, async ({ page }) => {
        await page.addInitScript(([t, d]) => {
          localStorage.setItem("doc-assistant.theme", t)
          localStorage.setItem("doc-assistant.mode", d ? "dark" : "light")
        }, [theme, dark] as const)
        await page.goto(route)
        await page.mouse.move(0, 0)
        const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
        expect(result.violations.filter((item) => item.impact === "serious" || item.impact === "critical")).toEqual([])
      })
    }
  }
  for (const viewport of [{ name: "desktop", width: 1280, height: 800 }, { name: "mobile", width: 390, height: 844 }]) {
    for (const route of ["fuentes", "ajustes", "sistema"]) {
      test(`captura ${route} ${theme} ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport)
        await page.addInitScript((t) => localStorage.setItem("doc-assistant.theme", t), theme)
        await page.goto(`/${route}`)
        await page.evaluate(() => document.fonts.ready)
        await page.screenshot({ path: path.join("..", "..", "evidence", "screenshots", `${route}-${theme}${viewport.name === "mobile" ? "-mobile" : ""}.png`), fullPage: true, animations: "disabled" })
      })
    }
  }
}
