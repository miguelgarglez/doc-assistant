import { expect, test } from "@playwright/test"

import { mockBackend, SOURCES } from "./mocks"

const rows = (page: import("@playwright/test").Page) => page.getByTestId("source-row")

test.describe("fuentes", () => {
  test("tabla con nombre, tipo, páginas, fragmentos, estado y fecha", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/fuentes")
    await expect(rows(page)).toHaveCount(3)
    const first = rows(page).first()
    await expect(first).toContainText("F-2026-001")
    await expect(first).toContainText("Factura")
    await expect(first).toContainText("Revisar")
    await expect(first).toContainText("31 oct 2026")
    const pdf = rows(page).filter({ hasText: "Ficha técnica de la pinza GR-50" })
    await expect(pdf).toContainText("ACME-DEMO-DS")
    await expect(pdf).toContainText("Documento")
    await expect(pdf).toContainText("Indexada")
    await expect(rows(page).filter({ hasText: "escaneo-sin-texto" })).toContainText("Sin texto")
  })

  test("filtro por tipo, búsqueda y orden", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/fuentes")
    await page.getByTestId("filter-pdf").click()
    await expect(rows(page)).toHaveCount(2)
    await page.getByTestId("filter-invoice").click()
    await expect(rows(page)).toHaveCount(1)
    await expect(page.getByTestId("filter-all")).toContainText("3")
    await page.getByTestId("filter-all").click()
    await page.getByLabel("Buscar fuentes por nombre").fill("escaneo")
    await expect(rows(page)).toHaveCount(1)
    await page.getByLabel("Buscar fuentes por nombre").fill("nada que coincida")
    await expect(page.getByTestId("sources-empty")).toContainText("Ninguna fuente coincide")
    await page.getByLabel("Buscar fuentes por nombre").fill("")
    await page.getByRole("button", { name: /^Nombre/ }).click()
    await expect(rows(page).first()).toContainText("escaneo-sin-texto")
    await page.getByRole("button", { name: /^Nombre/ }).click()
    await expect(rows(page).first()).toContainText("Ficha técnica")
  })

  test("sin fuentes: estado vacío con la acción para añadir", async ({ page }) => {
    await mockBackend(page, { sources: [] })
    await page.goto("/fuentes")
    await expect(page.getByTestId("sources-empty")).toContainText("Todavía no hay fuentes")
    await expect(page.getByTestId("upload-trigger")).toBeVisible()
  })

  test("detalle de un documento: fragmentos y página con navegación", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/fuentes")
    await rows(page).filter({ hasText: "ACME-DEMO-DS" }).getByRole("button").first().click()
    const detail = page.getByTestId("source-detail")
    await expect(detail).toBeVisible()
    await expect(detail).toContainText("2 páginas · 4 fragmentos")
    await expect(detail.getByTestId("chunk-list").getByRole("listitem")).toHaveCount(2)
    await detail.getByRole("button", { name: "Página", exact: true }).click()
    await expect(detail.getByAltText("Página 1 de ACME-DEMO-DS")).toBeVisible()
    await detail.getByRole("button", { name: "Página siguiente" }).click()
    await expect(detail.getByAltText("Página 2 de ACME-DEMO-DS")).toBeVisible()
    await expect(detail.getByRole("button", { name: "Página siguiente" })).toBeDisabled()
    await detail.getByRole("button", { name: "Cerrar detalle" }).click()
    await expect(detail).toHaveCount(0)
  })

  test("detalle de una factura: campos extraídos, motivo e imagen", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/fuentes")
    await page.getByTestId("filter-invoice").click()
    await rows(page).first().getByRole("button").first().click()
    const detail = page.getByTestId("source-detail")
    await expect(detail.getByTestId("invoice-fields")).toContainText("537,94 €")
    await expect(detail.getByTestId("invoice-fields")).toContainText("Talleres Puig, S.A.")
    await expect(detail).toContainText("El IVA no cuadra")
    await expect(detail.getByAltText("Imagen de la factura F-2026-001")).toBeVisible()
  })

  test("quitar una fuente pide confirmación y la saca de la lista", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/fuentes")
    await rows(page).filter({ hasText: "escaneo-sin-texto" }).getByRole("button").first().click()
    await page.getByTestId("remove-source").click()
    const dialog = page.getByRole("dialog")
    await expect(dialog).toContainText("Quitar «escaneo-sin-texto» del índice")
    await dialog.getByRole("button", { name: "Cancelar" }).click()
    await expect(rows(page)).toHaveCount(3)
    await page.getByTestId("remove-source").click()
    await page.getByTestId("confirm-remove").click()
    await expect(rows(page)).toHaveCount(2)
    await expect(page.getByText("Se quitó escaneo-sin-texto del índice")).toBeVisible()
    await expect(page.getByTestId("source-detail")).toHaveCount(0)
  })

  test("subida: estados visibles, progreso y la lista se actualiza al terminar", async ({ page }) => {
    await mockBackend(page)
    let added = false
    await page.route("**/api/sources", (route) =>
      route.fulfill({
        json: added ? [{ ...SOURCES[0], id: "pdf-nuevo", name: "manual-nuevo", title: "Manual nuevo", added_at: "2026-10-31T12:00:00+00:00" }, ...SOURCES] : SOURCES,
      })
    )
    await page.route("**/api/documents", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 600))
      added = true
      await route.fulfill({
        json: { n_chunks: 12, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-nuevo", path: "p", content_hash: "h", created: true },
      })
    })
    await page.goto("/fuentes")
    await expect(rows(page)).toHaveCount(3)
    await page.getByTestId("sources-file-input").setInputFiles({
      name: "manual-nuevo.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 demo"),
    })
    const row = page.getByTestId("upload-row")
    await expect(row).toContainText("manual-nuevo.pdf")
    await expect(row).toHaveAttribute("data-status", /uploading|processing|queued/)
    await expect(row).toHaveAttribute("data-status", "done")
    await expect(row).toContainText("12 fragmentos")
    await expect(rows(page)).toHaveCount(4)
    await row.getByRole("button", { name: /Quitar manual-nuevo.pdf de la lista/ }).click()
    await expect(row).toHaveCount(0)
  })

  test("subida fallida muestra el motivo y se puede reintentar; un tipo no admitido no", async ({ page }) => {
    await mockBackend(page)
    let calls = 0
    await page.route("**/api/documents", async (route) => {
      calls += 1
      if (calls === 1) {
        await route.fulfill({ status: 413, json: { code: "file_too_large", message: "El archivo supera el máximo permitido." } })
        return
      }
      await route.fulfill({
        json: { n_chunks: 3, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-z", path: "p", content_hash: "h", created: false },
      })
    })
    await page.goto("/fuentes")
    await page.getByTestId("sources-file-input").setInputFiles([
      { name: "grande.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") },
      { name: "notas.txt", mimeType: "text/plain", buffer: Buffer.from("hola") },
    ])
    const big = page.getByTestId("upload-row").filter({ hasText: "grande.pdf" })
    await expect(big).toHaveAttribute("data-status", "error")
    await expect(big).toContainText("El archivo supera el máximo permitido.")
    const txt = page.getByTestId("upload-row").filter({ hasText: "notas.txt" })
    await expect(txt).toContainText("Solo se admiten PDF e imágenes")
    await expect(txt.getByRole("button", { name: /Reintentar/ })).toHaveCount(0)
    await big.getByRole("button", { name: "Reintentar grande.pdf" }).click()
    await expect(big).toHaveAttribute("data-status", "done")
    await expect(big).toContainText("Ya estaba indexado")
  })

  test("sin scroll de página con la tabla y el detalle abiertos", async ({ page }) => {
    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 1280, height: 720 },
    ]) {
      await page.setViewportSize(viewport)
      await mockBackend(page)
      await page.goto("/fuentes")
      await rows(page).first().getByRole("button").first().click()
      await expect(page.getByTestId("source-detail")).toBeVisible()
      const overflow = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
      expect(overflow).toBeLessThanOrEqual(0)
    }
  })

  test.describe("móvil", () => {
    test.use({ viewport: { width: 390, height: 844 } })
    test("el detalle se abre en una hoja inferior", async ({ page }) => {
      await mockBackend(page)
      await page.goto("/fuentes")
      await expect(rows(page)).toHaveCount(3)
      await rows(page).filter({ hasText: "ACME-DEMO-DS" }).getByRole("button").first().click()
      const detail = page.getByTestId("source-detail")
      await expect(detail).toBeVisible()
      expect((await detail.boundingBox())!.y).toBeGreaterThan(80)
      await detail.getByRole("button", { name: "Cerrar detalle" }).click()
      await expect(detail).toHaveCount(0)
    })
  })
})
