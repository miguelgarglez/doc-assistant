import path from "node:path"

import { expect, test, type Page } from "@playwright/test"

import {
  askAnswerWithCitation,
  askError,
  askRefusal,
  PAGE_PNG_BASE64,
} from "./fixtures"

const SCREENSHOT_DIR = path.join("..", "..", "evidence", "screenshots")

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

test.describe("ask flow screenshots", () => {
  test("respuesta con cita y visor de fuente", async ({ page }) => {
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
        body: Buffer.from(PAGE_PNG_BASE64, "base64"),
      })
    })

    await page.goto("/")
    await stabilize(page)

    await page.getByLabel("Pregunta").fill("¿Puedo deducir el IVA de material de oficina?")
    await page.getByRole("button", { name: "Consultar" }).click()

    await expect(page.getByText(askAnswerWithCitation.answer)).toBeVisible()
    await page
      .getByRole("button", { name: /Ver fuente: Manual IVA 2024/ })
      .click()
    const pageImage = page.getByRole("img", {
      name: /Página 14 de Manual IVA 2024/,
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

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "ask-answer-with-source.png"),
      fullPage: true,
    })
  })

  test("rechazo", async ({ page }) => {
    await page.route("**/api/ask", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(askRefusal),
      })
    })

    await page.goto("/")
    await stabilize(page)

    await page.getByLabel("Pregunta").fill("¿Cómo eludo el IVA?")
    await page.getByRole("button", { name: "Consultar" }).click()

    await expect(page.getByTestId("refusal-notice")).toBeVisible()
    await expect(page.getByText(askRefusal.reason)).toBeVisible()

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "ask-refusal.png"),
      fullPage: true,
    })
  })

  test("error tipado del API", async ({ page }) => {
    await page.route("**/api/ask", async (route) => {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify(askError),
      })
    })

    await page.goto("/")
    await stabilize(page)

    await page.getByLabel("Pregunta").fill("¿Cuál es el tipo general de IVA?")
    await page.getByRole("button", { name: "Consultar" }).click()

    await expect(page.getByTestId("ask-error-notice")).toBeVisible()
    await expect(page.getByText(askError.message)).toBeVisible()
    await expect(page.getByText(`Error (${askError.code})`)).toBeVisible()

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "ask-error.png"),
      fullPage: true,
    })
  })
})
