import { expect, test } from "@playwright/test"

import { answerEvents, ask, mockBackend, sse } from "./mocks"

test.describe("sistema", () => {
  test("estado y latencia por pieza, con texto además de color", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/sistema")
    await expect(page.getByTestId("piece-web")).toContainText("Operativo")
    await expect(page.getByTestId("piece-proxy")).toContainText("Operativo")
    await expect(page.getByTestId("piece-proxy")).toContainText("ms")
    await expect(page.getByTestId("piece-llm")).toContainText("Operativo")
    await expect(page.getByTestId("piece-llm")).toContainText("3,1 ms")
    await expect(page.getByTestId("piece-llm")).toContainText("127.0.0.1:8081")
    await expect(page.getByTestId("piece-reranker")).toContainText("Cargando o lento")
    await expect(page.getByTestId("piece-ocr")).toContainText("No disponible")
    await expect(page.getByTestId("piece-sqlite")).toContainText("4 fragmentos")
    await expect(page.getByTestId("health-checked")).toBeVisible()
  })

  test("sin consulta previa explica cómo ver la traza", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/sistema")
    await expect(page.getByTestId("trace-empty")).toContainText("Todavía no hay ninguna consulta")
    await expect(page.getByTestId("replay-trace")).toBeDisabled()
    await expect(page.getByTestId("piece-llm")).toHaveAttribute("data-lit", "idle")
  })

  test("muestra el código de un fallo temprano y no ofrece reproducir pasos ausentes", async ({ page }) => {
    await mockBackend(page, {
      ask: (route) => route.fulfill({
        contentType: "text/event-stream",
        body: sse([["error", { code: "model_busy", message: "El modelo está ocupado. Inténtalo de nuevo." }]]),
      }),
    })
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await expect(page.getByTestId("ask-error-notice")).toContainText("El modelo está ocupado")
    await expect(page.getByTestId("ask-error-notice")).not.toContainText("model_busy")
    await page.getByRole("link", { name: "Sistema" }).click()
    await expect(page.getByTestId("trace-code")).toHaveText("model_busy")
    await expect(page.getByTestId("replay-trace")).toBeDisabled()
  })

  test("la última consulta aparece con sus pasos y el tiempo de cada pieza; al pasar por un paso se ilumina su pieza", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
    await page.getByRole("link", { name: "Sistema" }).click()
    await expect(page).toHaveURL(/\/sistema$/)
    await expect(page.getByTestId("trace-question")).toContainText("¿Carga útil?")
    await expect(page.getByTestId("trace-question")).toContainText("1,3 s en total")
    await expect(page.getByTestId("trace-step-generate")).toContainText("Respuesta redactada")
    await expect(page.getByTestId("trace-step-generate")).toContainText("1,2 s")
    await expect(page.getByTestId("usage-llm")).toContainText("1,2 s")
    await expect(page.getByTestId("usage-embeddings")).toContainText("50 ms")

    await page.getByTestId("trace-step-generate").hover()
    await expect(page.getByTestId("piece-llm")).toHaveAttribute("data-lit", "working")
    await expect(page.getByTestId("piece-proxy")).toHaveAttribute("data-lit", "carrier")
    await expect(page.getByTestId("piece-reranker")).toHaveAttribute("data-lit", "idle")
    await page.getByTestId("trace-step-retrieve").hover()
    await expect(page.getByTestId("piece-embeddings")).toHaveAttribute("data-lit", "working")
    await expect(page.getByTestId("piece-sqlite")).toHaveAttribute("data-lit", "working")
    await expect(page.getByTestId("piece-llm")).toHaveAttribute("data-lit", "idle")
  })

  test("reproducir recorre los pasos iluminando las piezas", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
    await page.getByRole("link", { name: "Sistema" }).click()
    await expect(page).toHaveURL(/\/sistema$/)
    await page.getByTestId("replay-trace").click()
    await expect(page.getByTestId("replay-trace")).toBeDisabled()
    await expect(page.getByTestId("piece-embeddings")).toHaveAttribute("data-lit", "working")
    await expect(page.getByTestId("piece-llm")).toHaveAttribute("data-lit", "working")
    await expect(page.getByTestId("replay-trace")).toBeEnabled({ timeout: 8000 })
    await expect(page.getByTestId("piece-llm")).toHaveAttribute("data-lit", "idle")
  })

  test("el proxy caído y un servicio sin /health/components se distinguen", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/health/components", (route) => route.fulfill({ status: 404, json: { code: "not_found", message: "x" } }))
    await page.goto("/sistema")
    await expect(page.getByTestId("piece-ai")).toContainText("Cargando o lento")
    await expect(page.getByTestId("piece-ai")).toContainText("No expone el estado de las piezas")
    await expect(page.getByTestId("piece-llm")).toContainText("Sin medir")

    await page.route("**/api/health", (route) => route.abort())
    await page.getByRole("button", { name: "Comprobar" }).click()
    await expect(page.getByTestId("piece-proxy")).toContainText("No disponible")
  })

  test("una consulta en curso ilumina la pieza que trabaja", async ({ page }) => {
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => (release = resolve))
    await mockBackend(page, {
      ask: async (route) => {
        await gate
        await route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents()) })
      },
    })
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await page.getByRole("link", { name: "Sistema" }).click()
    await expect(page).toHaveURL(/\/sistema$/)
    release()
    await expect(page.getByTestId("trace-step-verify")).toBeVisible()
  })

  test("Sistema mantiene la página fija y permite alcanzar el historial", async ({ page }) => {
    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 1280, height: 720 },
    ]) {
      await page.setViewportSize(viewport)
      await mockBackend(page)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
      await page.getByRole("link", { name: "Sistema" }).click()
      await expect(page).toHaveURL(/\/sistema$/)
      await expect(page.getByTestId("trace-step-verify")).toBeVisible()
      const overflow = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
      expect(overflow).toBeLessThanOrEqual(0)
      const history = page.getByRole("region", { name: "Historial y revisión" })
      await history.scrollIntoViewIfNeeded()
      await expect(history.getByText("Retención: 30 días")).toBeVisible()
      await page.evaluate(() => window.sessionStorage.clear())
      await page.goto("/")
    }
  })
})
