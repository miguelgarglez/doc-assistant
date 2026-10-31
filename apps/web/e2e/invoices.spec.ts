import path from "node:path"

import { expect, test, type Page } from "@playwright/test"

import {
  FACTURA_001_PATH,
  FACTURA_001_PNG,
  invoiceOkRecord,
  invoiceOkUpload,
  invoiceReviewUpload,
} from "./invoice-fixtures"

test.beforeEach(async ({ page }) => {
  await page.route("**/api/ask/stream", (route) => route.fulfill({ status: 404 }))
})

const SCREENSHOT_DIR = path.join("..", "..", "evidence", "screenshots")

const VIEWPORTS = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 390, height: 844 },
} as const

async function stabilize(page: Page) {
  await page.evaluate(() => document.fonts.ready)
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
    `,
  })
}

async function openFacturas(page: Page) {
  if (await page.getByText("Menú", { exact: true }).isVisible()) await page.getByText("Menú", { exact: true }).click()
  await page.getByRole("link", { name: "Fuentes", exact: true }).click()
  await expect(page.getByTestId("invoices-workspace")).toBeVisible()
}

async function mockInvoiceApis(
  page: Page,
  uploadBody: typeof invoiceOkUpload | typeof invoiceReviewUpload
) {
  let listed: unknown[] = []

  await page.route("**/api/invoices/upload", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback()
      return
    }
    listed = [uploadBody.record]
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(uploadBody),
    })
  })

  await page.route("**/api/invoices", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(listed),
    })
  })

  await page.route("**/api/invoices/*/image", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: FACTURA_001_PNG,
    })
  })
}

async function uploadAndShowCard(page: Page, expectedEstado: string) {
  await openFacturas(page)
  await page
    .getByTestId("invoice-upload")
    .locator('input[type="file"]')
    .setInputFiles(FACTURA_001_PATH)

  await expect(page.getByTestId("invoice-review-card")).toBeVisible()
  await expect(page.getByTestId("invoice-estado")).toHaveText(expectedEstado)

  const image = page.getByRole("img", { name: /Factura / })
  await expect(image).toBeVisible()
  await expect
    .poll(async () =>
      image.evaluate((el) => (el as HTMLImageElement).naturalWidth)
    )
    .toBeGreaterThan(0)
}

async function captureInvoice(
  page: Page,
  name: string,
  viewport: keyof typeof VIEWPORTS,
  uploadBody: typeof invoiceOkUpload | typeof invoiceReviewUpload,
  assertions: () => Promise<void>
) {
  await page.setViewportSize(VIEWPORTS[viewport])
  await mockInvoiceApis(page, uploadBody)
  await page.goto("/")
  await stabilize(page)
  await uploadAndShowCard(page, uploadBody.estado)
  await assertions()
  const suffix = viewport === "desktop" ? "" : "-mobile"
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, `${name}${suffix}.png`),
    fullPage: true,
  })
}

test.describe("invoice flow screenshots", () => {
  for (const viewport of ["desktop", "mobile"] as const) {
    test(`factura ok (${viewport})`, async ({ page }) => {
      await captureInvoice(page, "invoice-ok", viewport, invoiceOkUpload, async () => {
        await expect(
          page.locator('[data-field="emisor"]')
        ).toContainText(invoiceOkRecord.emisor)
        await expect(
          page.locator('[data-field="importe_total"]')
        ).toContainText("537,94 €")
        await expect(
          page.locator('[data-field="iban"]')
        ).toContainText("—  no encontrado")
        await expect(page.getByTestId("invoice-list-item-F-2026-001")).toBeVisible()
      })
    })

    test(`factura revisar (${viewport})`, async ({ page }) => {
      await captureInvoice(
        page,
        "invoice-review",
        viewport,
        invoiceReviewUpload,
        async () => {
          await expect(page.getByTestId("invoice-motivo")).toContainText(
            "importes_incompletos"
          )
          await expect(
            page.getByTestId("flag-derivado-base_imponible_total")
          ).toBeVisible()
          await expect(
            page.locator('[data-field="cuota_iva_total"]')
          ).toContainText("—  no encontrado")
          await expect(
            page.locator('[data-field="iban"]')
          ).toContainText("—  no encontrado")
        }
      )
    })
  }
})
