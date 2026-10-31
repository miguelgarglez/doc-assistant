import { expect, test } from "@playwright/test"

/**
 * Against the real stack (web + AI service + llama models). Skipped unless LIVE_BASE_URL is set:
 *   LIVE_BASE_URL=http://127.0.0.1:3110 pnpm exec playwright test e2e/live.spec.ts
 * Expects the fictional demo sources (robot TX-10, sensor SX-20) to be indexed.
 */
const LIVE = process.env.LIVE_BASE_URL

test.describe("stack real", () => {
  test.skip(!LIVE, "LIVE_BASE_URL no definido")
  test.use({ baseURL: LIVE })
  test.setTimeout(180_000)

  test("una pregunta sobre las fuentes devuelve respuesta con citas y el visor abre el fragmento", async ({ page }) => {
    await page.goto("/")
    await page.getByLabel("Pregunta", { exact: true }).fill("¿Qué alcance tiene el sensor SX-20?")
    await page.keyboard.press("Enter")
    const answer = page.locator('[data-testid="assistant-message"][data-kind="answer"]').first()
    await expect(answer).toBeVisible({ timeout: 120_000 })
    await expect(page.getByTestId("citation-1").first()).toBeVisible()
    await page.getByTestId("citation-1").first().click()
    await expect(page.getByTestId("source-viewer")).toBeVisible()
  })

  test("una pregunta sin respaldo en las fuentes se rechaza con diseño propio", async ({ page }) => {
    await page.goto("/")
    await page.getByLabel("Pregunta", { exact: true }).fill("¿Quién ganó el mundial de fútbol de 1998?")
    await page.keyboard.press("Enter")
    await expect(page.locator('[data-testid="assistant-message"][data-kind="refusal"]').first()).toBeVisible({
      timeout: 120_000,
    })
  })

  test("Sistema muestra las piezas reales y la traza de la última consulta", async ({ page }) => {
    await page.goto("/")
    await page.getByLabel("Pregunta", { exact: true }).fill("¿Qué alcance tiene el sensor SX-20?")
    await page.keyboard.press("Enter")
    await expect(page.locator('[data-testid="assistant-message"]').first()).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('[data-testid="assistant-message"][data-kind="answer"], [data-testid="assistant-message"][data-kind="refusal"]').first()).toBeVisible({ timeout: 120_000 })
    await page.goto("/sistema")
    for (const piece of ["web", "proxy", "llm", "embeddings", "reranker", "ocr", "sqlite"]) {
      await expect(page.getByTestId(`piece-${piece}`)).toBeVisible()
    }
    await expect(page.getByTestId("piece-llm")).toContainText("Operativo")
    await expect(page.getByTestId("trace-empty")).toHaveCount(0)
  })

  test("Fuentes lista los documentos indexados", async ({ page }) => {
    await page.goto("/fuentes")
    await expect(page.getByRole("table")).toBeVisible()
    await expect(page.getByRole("row").nth(1)).toBeVisible()
  })
})
