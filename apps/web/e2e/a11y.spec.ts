import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

import { ask, mockBackend } from "./mocks"

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
