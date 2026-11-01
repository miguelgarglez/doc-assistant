import { expect, test, type Page } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

import { mockBackend, SOURCES, sse } from "./mocks"

const toast = (page: Page) => page.getByTestId("upload-toast")
const row = (page: Page, name: string) => toast(page).getByTestId("upload-row").filter({ hasText: name })
const pdf = (name: string) => ({ name, mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 demo") })

const created = (chunks: number) => ({
  json: { n_chunks: chunks, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-nuevo", path: "p", content_hash: "h", created: true },
})

async function openDialog(page: Page) {
  await page.getByTestId("add-sources").click()
  await expect(page.getByTestId("add-sources-dialog")).toBeVisible()
}

/** Stage events the service would send for a job, whatever the id. */
async function mockStages(page: Page, stages: string[]) {
  await page.route("**/api/ingest/jobs/*/events", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: sse(stages.map((stage, seq) => ["stage", { stage, label: stage, seq, detail: {} }])),
    })
  )
}

test.describe("añadir fuentes", () => {
  for (const theme of ["industrial", "neutral"]) {
    for (const mode of ["light", "dark"]) {
      test(`aviso de error accesible en ${theme} ${mode}`, async ({ page }) => {
        await page.addInitScript(([t, m]) => {
          localStorage.setItem("doc-assistant.theme", t)
          localStorage.setItem("doc-assistant.mode", m)
        }, [theme, mode])
        await mockBackend(page)
        await page.goto("/")
        await openDialog(page)
        await page.getByTestId("sources-file-input").setInputFiles({ name: "invalido.txt", mimeType: "text/plain", buffer: Buffer.from("prueba") })
        await expect(toast(page)).toBeVisible()
        await expect(page.getByTestId("add-sources-dialog")).toHaveCount(0)
        await page.waitForTimeout(500) // Let the toast entrance finish before measuring contrast.
        expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
      })
    }
  }
  test("el aviso de errores permanece visible y permite cerrar cada archivo", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles([
      { name: "uno.txt", mimeType: "text/plain", buffer: Buffer.from("uno") },
      { name: "dos.txt", mimeType: "text/plain", buffer: Buffer.from("dos") },
    ])
    await page.setViewportSize({ width: 375, height: 500 })
    await toast(page).hover()
    await expect(toast(page)).toBeVisible()
    await page.waitForTimeout(500) // Measure after Sonner's entrance and expansion transitions.
    const box = await toast(page).boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(375)
    expect(box!.y + box!.height).toBeLessThanOrEqual(500)
    await page.getByRole("button", { name: "Cerrar error de uno.txt" }).click()
    await expect(row(page, "uno.txt")).toHaveCount(0)
    await expect(row(page, "dos.txt")).toBeVisible()
    await page.getByTestId("upload-toast-close").click()
    await expect(toast(page)).toHaveCount(0)
  })

  test("el aviso y otras notificaciones caben juntos en una ventana baja", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/history/status", (route) => route.fulfill({ json: {
      active: false, enabled: true, retention_days: 30, pending: 0, initialization_error: null,
      failures: [{ request_id: "prueba-sintetica", error: "OSError" }],
    } }))
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(Array.from({ length: 8 }, (_, n) => ({
      name: `${n}.txt`, mimeType: "text/plain", buffer: Buffer.from("prueba"),
    })))
    await page.getByRole("link", { name: "Sistema" }).click()
    const copyButton = page.getByRole("button", { name: "Copiar identificador prueba-sintetica" })
    await copyButton.click()
    const copyToast = page.getByText(/Identificador copiado|No se pudo copiar el identificador/)
    await expect(copyToast).toHaveCount(1)
    await copyButton.click()
    await expect(copyToast).toHaveCount(2)
    await page.setViewportSize({ width: 375, height: 320 })
    await copyToast.first().hover()
    await page.waitForTimeout(500)
    for (const element of [toast(page), copyToast.first(), copyToast.last()]) {
      const box = await element.boundingBox()
      expect(box).not.toBeNull()
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.y).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(375)
      expect(box!.y + box!.height).toBeLessThanOrEqual(320)
    }
  })

  test("botón grande en la barra lateral y diálogo con zona de suelta", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    const button = page.getByTestId("add-sources")
    await expect(button).toBeVisible()
    expect((await button.boundingBox())!.height).toBeGreaterThanOrEqual(36)
    await openDialog(page)
    const zone = page.getByTestId("dropzone")
    await expect(zone).toContainText("Arrastra archivos aquí")
    await expect(page.getByTestId("add-sources-dialog")).toContainText("PNG o JPG")
    await page.keyboard.press("Escape")
    await expect(page.getByTestId("add-sources-dialog")).toHaveCount(0)
  })

  test("arrastrar sobre la zona la resalta y soltar sube el archivo sin duplicarlo", async ({ page }) => {
    await mockBackend(page)
    let uploads = 0
    await page.route("**/api/documents*", (route) => {
      uploads += 1
      return route.fulfill(created(3))
    })
    await page.goto("/")
    await openDialog(page)
    const drag = (type: "dragenter" | "drop") =>
      page.getByTestId("dropzone").evaluate((element, kind) => {
        const data = new DataTransfer()
        data.items.add(new File(["%PDF-1.4"], "arrastrado.pdf", { type: "application/pdf" }))
        element.dispatchEvent(new DragEvent(kind, { dataTransfer: data, bubbles: true, cancelable: true }))
      }, type)
    await drag("dragenter")
    await expect(page.getByTestId("dropzone")).toHaveAttribute("data-over", "true")
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "0")
    await drag("drop")
    await expect(page.getByTestId("add-sources-dialog")).toHaveCount(0)
    await expect(row(page, "arrastrado.pdf")).toHaveAttribute("data-status", "done")
    expect(uploads).toBe(1)
  })

  test("el aviso muestra cada paso, sigue al navegar y lleva a Fuentes", async ({ page }) => {
    await mockBackend(page)
    await mockStages(page, ["received", "reading", "indexing"])
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => (release = resolve))
    await page.route("**/api/documents*", async (route) => {
      await gate
      await route.fulfill(created(12))
    })
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(pdf("manual-nuevo.pdf"))
    await expect(page.getByTestId("add-sources-dialog")).toHaveCount(0)

    const item = row(page, "manual-nuevo.pdf")
    await expect(item).toHaveAttribute("data-status", "processing")
    await expect(item.getByTestId("upload-status")).toHaveText("Indexando…")
    await expect(page.getByTestId("upload-toast-title")).toContainText("Añadiendo")

    await page.getByRole("link", { name: "Fuentes" }).click()
    await expect(page).toHaveURL(/\/fuentes$/)
    await expect(item).toHaveAttribute("data-status", "processing")

    release()
    await expect(item).toHaveAttribute("data-status", "done")
    await expect(item.getByTestId("upload-status")).toHaveText("12 fragmentos indexados")
    await expect(page.getByTestId("upload-toast-title")).toHaveText("Fuente añadida")

    await page.getByRole("link", { name: "Chat" }).click()
    await page.getByTestId("upload-toast-open").click()
    await expect(page).toHaveURL(/\/fuentes$/)
    await page.getByTestId("upload-toast-close").click()
    await expect(toast(page)).toHaveCount(0)
  })

  test("muestra el avance de procesamiento por archivo", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/ingest/jobs/*/events", (route) => route.fulfill({
      contentType: "text/event-stream",
      body: sse([["stage", { stage: "reading", label: "Leyendo", seq: 1, detail: { current: 12, total: 80 } }]]),
    }))
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => (release = resolve))
    await page.route("**/api/documents*", async (route) => {
      await gate
      await route.fulfill(created(3))
    })
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(pdf("largo.pdf"))
    await expect(row(page, "largo.pdf")).toContainText("Leyendo páginas: 12 de 80")
    release()
    await expect(row(page, "largo.pdf")).toHaveAttribute("data-status", "done")
  })

  test("la lista de Fuentes se actualiza al terminar", async ({ page }) => {
    await mockBackend(page)
    let added = false
    await page.route("**/api/sources", (route) =>
      route.fulfill({
        json: added ? [{ ...SOURCES[0], id: "pdf-nuevo", name: "manual-nuevo", title: "Manual nuevo", added_at: "2026-10-31T12:00:00+00:00" }, ...SOURCES] : SOURCES,
      })
    )
    await page.route("**/api/documents*", (route) => {
      added = true
      return route.fulfill(created(12))
    })
    await page.goto("/fuentes")
    await expect(page.getByTestId("source-row")).toHaveCount(3)
    await page.getByTestId("upload-trigger").click()
    await page.getByTestId("sources-file-input").setInputFiles(pdf("manual-nuevo.pdf"))
    await expect(row(page, "manual-nuevo.pdf")).toHaveAttribute("data-status", "done")
    await expect(page.getByTestId("source-row")).toHaveCount(4)
    await expect(page.getByTestId("upload-toast-open")).toHaveCount(0)
  })

  test("errores con el motivo en español, reintento y tipos no admitidos sin reintento", async ({ page }) => {
    await mockBackend(page)
    let calls = 0
    await page.route("**/api/documents*", (route) => {
      calls += 1
      if (calls === 1) {
        return route.fulfill({ status: 502, json: { code: "model_busy", message: "llm unavailable" } })
      }
      return route.fulfill(created(3))
    })
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles([pdf("grande.pdf"), { name: "notas.txt", mimeType: "text/plain", buffer: Buffer.from("hola") }])
    const big = row(page, "grande.pdf")
    await expect(big).toHaveAttribute("data-status", "error")
    await expect(big).toContainText("El servicio está ocupado")
    await expect(row(page, "notas.txt")).toContainText("Solo se admiten PDF e imágenes")
    await expect(row(page, "notas.txt").getByRole("button", { name: /Reintentar/ })).toHaveCount(0)
    await expect(page.getByTestId("upload-toast-title")).toHaveText("No se pudieron añadir 2 archivos")
    await big.getByRole("button", { name: "Reintentar grande.pdf" }).click()
    await expect(big).toHaveAttribute("data-status", "done")
    await expect(page.getByTestId("upload-toast-title")).toHaveText("1 añadida, 1 con error")
  })

  test("un archivo demasiado grande se explica y no ofrece reintento", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/documents*", (route) => route.fulfill({ status: 413, json: { code: "upload_too_large", message: "PDF exceeds upload limit" } }))
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(pdf("enorme.pdf"))
    const item = row(page, "enorme.pdf")
    await expect(item).toContainText("supera el tamaño máximo")
    await expect(item.getByRole("button", { name: /Reintentar/ })).toHaveCount(0)
  })

  test("explica límites, protección, timeout y errores internos", async ({ page }) => {
    await mockBackend(page)
    const errors = [
      { code: "upload_too_large", message: "limit", reason: "page_limit", limit: 200 },
      { code: "upload_too_large", message: "limit", reason: "size_limit", limit: 1024 },
      { code: "invalid_file", message: "invalid", reason: "pdf_protected" },
      { code: "invalid_file", message: "invalid", reason: "pdf_unreadable" },
      { code: "model_timeout", message: "timeout" },
      { code: "internal_error", message: "secret" },
    ]
    let index = 0
    await page.route("**/api/documents*", (route) => route.fulfill({ status: 400, json: errors[index++] }))
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(errors.map((_, n) => pdf(`${n}.pdf`)))
    const cases = [
      ["0.pdf", "200 páginas", false], ["1.pdf", "1024 bytes", false],
      ["2.pdf", "protegido", false], ["3.pdf", "No se puede leer", false],
      ["4.pdf", "tardó demasiado", true], ["5.pdf", "error interno", false],
    ] as const
    for (const [name, message, retry] of cases) {
      const item = row(page, name)
      await expect(item).toContainText(message)
      await expect(item.getByRole("button", { name: /Reintentar/ })).toHaveCount(retry ? 1 : 0)
    }
    await expect(row(page, "5.pdf")).not.toContainText("secret")
  })

  test("un archivo repetido se dice, no se presenta como añadido", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/documents*", (route) =>
      route.fulfill({ json: { n_chunks: 3, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-z", path: "p", content_hash: "h", created: false } })
    )
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles(pdf("repetido.pdf"))
    await expect(row(page, "repetido.pdf").getByTestId("upload-status")).toHaveText("Ya estaba indexado, no se añadió de nuevo")
  })

  test("las facturas pasan por OCR y extracción y se dice en cada paso", async ({ page }) => {
    await mockBackend(page)
    await mockStages(page, ["received", "ocr", "extracting", "indexing"])
    await page.route("**/api/invoices/upload*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 300))
      await route.fulfill({ json: { record: { numero: "F-1" }, estado: "ok", evidencias: {}, flags: {} } })
    })
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles({ name: "factura.png", mimeType: "image/png", buffer: Buffer.from("png") })
    const item = row(page, "factura.png")
    await expect(item).toHaveAttribute("data-status", "done")
    await expect(item.getByTestId("upload-status")).toHaveText("Factura extraída")
  })

  test("cancelar: en cola se quita y mientras sube corta la subida; ya en proceso no se ofrece", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/documents*", () => new Promise(() => undefined))
    await page.goto("/")
    await openDialog(page)
    await page.getByTestId("sources-file-input").setInputFiles([pdf("primero.pdf"), pdf("segundo.pdf")])
    const second = row(page, "segundo.pdf")
    await expect(second).toHaveAttribute("data-status", "queued")
    await second.getByRole("button", { name: "Cancelar segundo.pdf" }).click()
    await expect(second).toHaveCount(0)
    const first = row(page, "primero.pdf")
    await expect(first.getByRole("button", { name: "Cancelar primero.pdf" })).toBeVisible()
    await first.getByRole("button", { name: "Cancelar primero.pdf" }).click()
    await expect(first).toHaveAttribute("data-status", "error")
    await expect(first).toContainText("Subida cancelada")
  })

  test("arrastrar un archivo a la ventana sin el diálogo sigue mostrando la zona de suelta", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/documents*", (route) => route.fulfill(created(2)))
    await page.goto("/")
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "0")
    await page.evaluate(() => {
      const data = new DataTransfer()
      data.items.add(new File(["%PDF-1.4"], "suelto.pdf", { type: "application/pdf" }))
      document.body.dispatchEvent(new DragEvent("dragenter", { dataTransfer: data, bubbles: true, cancelable: true }))
    })
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "1")
  })
})
