import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

import { answerEvents, ask, CITATION, clarificationEvents, mockBackend, SECOND_CITATION, sse } from "./mocks"

test.use({ reducedMotion: "reduce" })

async function themed(page: Page, theme: "industrial" | "neutral", dark: boolean) {
  await page.addInitScript(
    ([t, d]) => {
      localStorage.setItem("doc-assistant.theme", t)
      localStorage.setItem("doc-assistant.mode", d ? "dark" : "light")
    },
    [theme, dark] as const
  )
}

async function expectNoSeriousViolations(page: Page) {
  await page.mouse.move(0, 0)
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
  const serious = results.violations.filter((item) => item.impact === "serious" || item.impact === "critical")
  expect(serious, JSON.stringify(serious.map((item) => ({ id: item.id, nodes: item.nodes.map((n) => n.html) })), null, 2)).toEqual([])
}

for (const theme of ["industrial", "neutral"] as const) {
  for (const dark of [false, true]) {
    const label = `${theme} ${dark ? "oscuro" : "claro"}`

    test(`chat vacío (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/")
      await expect(page.getByTestId("chat-empty")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`feedback con botón en hover (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
      await page.getByRole("button", { name: "Respuesta incorrecta" }).click()
      const submit = page.getByRole("button", { name: "Enviar para revisión" })
      await submit.hover()
      await submit.evaluate((element) => Promise.all(element.getAnimations().map((animation) => animation.finished)))
      expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
    })

    test(`chat con respuesta, citas y visor abierto (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
      await page.getByTestId("citation-1").click()
      await expect(page.getByTestId("source-viewer")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`aclaración de facturas con candidatas (${label})`, async ({ page }) => {
      await mockBackend(page, { ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(clarificationEvents()) }) })
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Cuál es el importe total de la factura?")
      await expect(page.getByTestId("clarification-notice")).toBeVisible()
      await expectNoSeriousViolations(page)
      await page.getByTestId("clarification-candidate").first().focus()
      await expectNoSeriousViolations(page)
    })

    test(`marcadores inline con vista previa y visor con resaltado (${label})`, async ({ page }) => {
      const text = "La carga útil es de 12 kg. La brida es ISO 9409-1-50-4-M6."
      const segments = [
        { text: "La carga útil es de 12 kg.", refs: [0] },
        { text: " La brida es ISO 9409-1-50-4-M6.", refs: [1] },
      ]
      await mockBackend(page, {
        ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(text, [CITATION, SECOND_CITATION], segments)) }),
      })
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("citation-marker-1")).toBeVisible()
      await page.getByTestId("citation-marker-1").hover()
      await expect(page.locator('[data-slot="hover-card-content"]')).toBeVisible()
      await expectNoSeriousViolations(page)
      await page.getByTestId("citation-marker-1").click()
      await expect(page.getByTestId("page-highlight")).toHaveCount(1)
      await expectNoSeriousViolations(page)
    })

    test(`añadir fuentes: diálogo y aviso de progreso (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.route("**/api/documents*", () => new Promise(() => undefined))
      await page.goto("/")
      await page.getByTestId("add-sources").click()
      await expect(page.getByTestId("dropzone")).toBeVisible()
      await expectNoSeriousViolations(page)
      await page.getByTestId("sources-file-input").setInputFiles({ name: "manual.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") })
      await expect(page.getByTestId("upload-toast")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`fuentes con detalle (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/fuentes")
      await page.getByTestId("source-row").filter({ hasText: "ACME-DEMO-DS" }).getByRole("button").first().click()
      await expect(page.getByTestId("chunk-list")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`sistema con traza (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
      await page.getByRole("link", { name: "Sistema" }).click()
      await expect(page.getByTestId("trace-step-verify")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`ajustes (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/ajustes")
      await expectNoSeriousViolations(page)
    })

    test(`design (${label})`, async ({ page }) => {
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/design")
      await expect(page.getByTestId("design-page")).toBeVisible()
      await expectNoSeriousViolations(page)
    })

    test(`móvil: chat y fuentes (${label})`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 })
      await mockBackend(page)
      await themed(page, theme, dark)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "answer")
      await expectNoSeriousViolations(page)
      await page.getByRole("button", { name: "Abrir el menú" }).click()
      await page.getByRole("link", { name: "Fuentes" }).click()
      await expect(page.getByTestId("source-row").first()).toBeVisible()
      await expectNoSeriousViolations(page)
    })
  }
}
