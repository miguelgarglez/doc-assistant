import path from "node:path"

import { expect, test, type Page } from "@playwright/test"

import {
  DEMO_QUESTION,
  askAnswerWithCitation,
  askError,
  askRefusal,
  PAGE_PNG,
} from "./fixtures"

const SCREENSHOT_DIR = path.join("..", "..", "evidence", "screenshots")

const VIEWPORTS = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 390, height: 844 },
} as const

async function stabilize(page: Page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
      html, body, button, input, textarea, p, h1, h2, h3, span, label, div {
        font-family: "Courier New", Courier, monospace !important;
        letter-spacing: 0 !important;
      }
    `,
  })
}

async function mockAskOk(page: Page) {
  await page.route("**/api/ask", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(askAnswerWithCitation),
    })
  })
  await page.route("**/api/sources/**/pages/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: PAGE_PNG,
    })
  })
}

async function captureFlow(
  page: Page,
  name: string,
  viewport: keyof typeof VIEWPORTS,
  run: () => Promise<void>
) {
  await page.setViewportSize(VIEWPORTS[viewport])
  await page.goto("/")
  await stabilize(page)
  await run()
  const suffix = viewport === "desktop" ? "" : "-mobile"
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, `${name}${suffix}.png`),
    fullPage: true,
  })
}

test.describe("ask flow screenshots", () => {
  for (const viewport of ["desktop", "mobile"] as const) {
    test(`respuesta con cita y visor (${viewport})`, async ({ page }) => {
      await mockAskOk(page)

      await captureFlow(page, "ask-answer-with-source", viewport, async () => {
        await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
        await page.getByRole("button", { name: "Consultar" }).click()

        await expect(page.getByText(askAnswerWithCitation.answer)).toBeVisible()
        await expect(
          page.getByRole("button", { name: /Ver fuente: ACME-DEMO-DS/ }).first()
        ).toBeVisible()

        const pageImage = page.getByRole("img", {
          name: /Página 1 de ACME-DEMO-DS/,
        })
        await expect(pageImage).toBeVisible()
        await expect
          .poll(async () =>
            pageImage.evaluate((el) => (el as HTMLImageElement).naturalWidth)
          )
          .toBeGreaterThan(0)
        await expect(page.locator("mark")).toHaveText(
          askAnswerWithCitation.citations[0].quote
        )

        if (askAnswerWithCitation.citations.length > 1) {
          await expect(
            page.getByRole("button", { name: "Cita siguiente" })
          ).toBeEnabled()
        }
      })
    })

    test(`rechazo (${viewport})`, async ({ page }) => {
      await page.route("**/api/ask", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(askRefusal),
        })
      })

      await captureFlow(page, "ask-refusal", viewport, async () => {
        await page
          .getByLabel("Pregunta")
          .fill("¿Cuál es el firmware secreto del controlador?")
        await page.getByRole("button", { name: "Consultar" }).click()

        await expect(page.getByTestId("refusal-notice")).toBeVisible()
        await expect(page.getByText(askRefusal.reason)).toBeVisible()
        await expect(
          page.getByText(
            "No hay evidencia en los documentos indexados; no se inventa una respuesta."
          )
        ).toBeVisible()
      })
    })

    test(`error tipado del API (${viewport})`, async ({ page }) => {
      await page.route("**/api/ask", async (route) => {
        await route.fulfill({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify(askError),
        })
      })

      await captureFlow(page, "ask-error", viewport, async () => {
        await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
        await page.getByRole("button", { name: "Consultar" }).click()

        await expect(page.getByTestId("ask-error-notice")).toBeVisible()
        await expect(page.getByText(askError.message)).toBeVisible()
        await expect(page.getByText(`Error (${askError.code})`)).toBeVisible()
        await expect(
          page.getByRole("button", { name: "Reintentar" })
        ).toBeVisible()
      })
    })
  }
})
