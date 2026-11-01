import { expect, test, type Page } from "@playwright/test"

import { segmentsMatch, withMarkers } from "../src/features/chat/lib/inline"
import { answerEvents, ask, CITATION, mockBackend, SECOND_CITATION, sse, type Segment } from "./mocks"

const assistant = (page: Page) => page.getByTestId("assistant-message")

const TEXT = "La carga útil máxima es de 12 kg. La interfaz de brida es ISO 9409-1-50-4-M6."
const SEGMENTS: Segment[] = [
  { text: "La carga útil máxima es de 12 kg.", refs: [0] },
  { text: " La interfaz de brida es ISO 9409-1-50-4-M6.", refs: [1] },
]

async function askWithSegments(page: Page, text = TEXT, segments = SEGMENTS) {
  await mockBackend(page, {
    ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(text, [CITATION, SECOND_CITATION], segments)) }),
  })
  await page.goto("/")
  await ask(page, "¿Carga útil y brida?")
  await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
}

test.describe("marcadores inline: funciones puras", () => {
  test("segmentos que reconstruyen el texto se aceptan", () => {
    expect(segmentsMatch(TEXT, SEGMENTS, 2)).toBe(true)
  })

  test("segmentos que no reconstruyen el texto, sin segmentos o con citas inexistentes se descartan", () => {
    expect(segmentsMatch(TEXT, [], 2)).toBe(false)
    expect(segmentsMatch(TEXT, [{ text: "otro texto", refs: [0] }], 2)).toBe(false)
    expect(segmentsMatch(TEXT, SEGMENTS, 1)).toBe(false)
    expect(segmentsMatch(TEXT, [{ text: TEXT, refs: [-1] }], 2)).toBe(false)
  })

  test("el marcador va pegado a la frase y antes del espacio que la separa de la siguiente", () => {
    const plain = withMarkers(TEXT, SEGMENTS, 2, "plain")
    expect(plain).toBe("La carga útil máxima es de 12 kg.[1] La interfaz de brida es ISO 9409-1-50-4-M6.[2]")
    const link = withMarkers(TEXT, SEGMENTS, 2, "link")
    expect(link).toContain("[1](#cite-1)")
    expect(link).toContain("[2](#cite-2)")
  })

  test("varias citas en un segmento dan varios marcadores; un segmento sin citas no lleva ninguno", () => {
    const segments: Segment[] = [
      { text: "Intro.", refs: [] },
      { text: "\n\n- Dato.", refs: [0, 1] },
    ]
    expect(withMarkers("Intro.\n\n- Dato.", segments, 2, "plain")).toBe("Intro.\n\n- Dato.[1][2]")
  })

  test("sin segmentos válidos el texto queda intacto", () => {
    expect(withMarkers(TEXT, [], 2)).toBe(TEXT)
    expect(withMarkers(TEXT, [{ text: "x", refs: [0] }], 2)).toBe(TEXT)
  })
})

test.describe("marcadores inline en el chat", () => {
  test("cada frase lleva su marcador y las citas ya no se repiten como píldoras", async ({ page }) => {
    await askWithSegments(page)
    const message = assistant(page)
    await expect(message.getByTestId("citation-marker-1")).toBeVisible()
    await expect(message.getByTestId("citation-marker-2")).toBeVisible()
    await expect(message.getByTestId("answer-text")).toHaveAttribute("data-inline", "true")
    await expect(message.getByTestId("citation-1")).toHaveCount(0)
    await expect(message.getByTestId("citations").getByText("2 fuentes")).toBeVisible()
    const first = message.getByTestId("citation-marker-1")
    const sentence = await message.getByTestId("answer-text").innerText()
    expect(sentence).toContain("12 kg.")
    const box = await first.boundingBox()
    const text = await message.getByTestId("answer-text").getByText("La carga útil máxima es de 12 kg.").boundingBox()
    expect(box && text && Math.abs(box.y - text.y) < text.height).toBe(true)
  })

  test("el hover enseña la cita con su fragmento y el clic abre el visor en esa cita", async ({ page }) => {
    await askWithSegments(page)
    const marker = assistant(page).getByTestId("citation-marker-2")
    await marker.hover()
    const card = page.locator('[data-slot="hover-card-content"]')
    await expect(card).toContainText("ACME-DEMO-DS")
    await expect(card).toContainText("ISO 9409-1-50-4-M6")
    await marker.click()
    const viewer = page.getByTestId("source-viewer")
    await expect(viewer).toBeVisible()
    await expect(viewer.getByTestId("viewer-position")).toHaveText("2/2")
    await expect(viewer.getByTestId("viewer-fragment").locator("mark")).toHaveText("ISO 9409-1-50-4-M6")
  })

  test("segmentos que no cuadran con el texto degradan a citas al final", async ({ page }) => {
    await askWithSegments(page, TEXT, [{ text: "otra cosa", refs: [0] }])
    const message = assistant(page)
    await expect(message.getByTestId("answer-text")).toHaveAttribute("data-inline", "false")
    await expect(message.getByTestId("citation-marker-1")).toHaveCount(0)
    await expect(message.getByTestId("citation-1")).toBeVisible()
    await expect(message.getByTestId("citation-2")).toBeVisible()
  })

  test("respuesta de metadatos: lista con viñetas válidas, sin viñetas vacías ni listas anidadas", async ({ page }) => {
    const text = [
      "Hay 2 documentos:",
      "",
      "- **ACME-DEMO-DS:** Ficha de la pinza. 2 páginas y 4 apartados.",
      "- **ACME-MANUAL:** Manual de operación. 12 páginas y 9 apartados.",
      "",
      "Pregúntame por cualquiera.",
    ].join("\n")
    const segments: Segment[] = [
      { text: "Hay 2 documentos:", refs: [] },
      { text: "\n\n- **ACME-DEMO-DS:** Ficha de la pinza. 2 páginas y 4 apartados.", refs: [0] },
      { text: "\n- **ACME-MANUAL:** Manual de operación. 12 páginas y 9 apartados.", refs: [1] },
      { text: "\n\nPregúntame por cualquiera.", refs: [] },
    ]
    await askWithSegments(page, text, segments)
    const body = assistant(page).getByTestId("answer-text")
    const items = body.getByRole("listitem")
    await expect(items).toHaveCount(2)
    for (const item of await items.all()) {
      expect((await item.innerText()).trim().length).toBeGreaterThan(20)
    }
    await expect(body.locator("li ol, li ul")).toHaveCount(0)
    await expect(body.locator("p")).toHaveCount(2)
    await expect(items.nth(0).getByTestId("citation-marker-1")).toBeVisible()
    await expect(items.nth(1).getByTestId("citation-marker-2")).toBeVisible()
  })

  test("copiar la respuesta conserva los marcadores [n]", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await askWithSegments(page)
    await assistant(page).getByTestId("copy-answer").click()
    const copied = await page.evaluate(() => navigator.clipboard.readText())
    expect(copied).toContain("12 kg.[1]")
    expect(copied).toContain("M6.[2]")
  })
})

test.describe("visor de página completa", () => {
  test("ocupa toda la ventana, resalta el fragmento y se maneja con el teclado", async ({ page }) => {
    await askWithSegments(page)
    await assistant(page).getByTestId("citation-marker-1").click()
    const viewer = page.getByTestId("source-viewer")
    const box = await viewer.boundingBox()
    const size = page.viewportSize()!
    expect(box!.width).toBeGreaterThanOrEqual(size.width - 1)
    expect(box!.height).toBeGreaterThanOrEqual(size.height - 1)

    await expect(viewer.getByTestId("page-highlight")).toHaveCount(1)
    await expect(viewer.getByTestId("viewer-notice")).toContainText("resaltado")
    const canvas = viewer.getByTestId("page-canvas")
    const initial = Number(await canvas.getAttribute("data-scale"))
    expect(initial).toBeGreaterThan(1)

    await page.keyboard.press("+")
    expect(Number(await canvas.getAttribute("data-scale"))).toBeGreaterThan(initial)
    await page.keyboard.press("0")
    await expect(canvas).toHaveAttribute("data-scale", "1.00")
    await page.keyboard.press("-")
    await expect(canvas).toHaveAttribute("data-scale", "1.00")

    await page.keyboard.press("ArrowRight")
    await expect(viewer.getByTestId("viewer-position")).toHaveText("2/2")
    await page.keyboard.press("ArrowRight")
    await expect(viewer.getByTestId("viewer-position")).toHaveText("2/2")
    await page.keyboard.press("ArrowLeft")
    await expect(viewer.getByTestId("viewer-position")).toHaveText("1/2")

    await page.keyboard.press("Escape")
    await expect(viewer).toHaveCount(0)
  })

  test("los botones de zoom y el doble clic acercan y ajustan", async ({ page }) => {
    await askWithSegments(page)
    await assistant(page).getByTestId("citation-marker-1").click()
    const canvas = page.getByTestId("page-canvas")
    await page.getByRole("button", { name: "Ajustar a la ventana" }).click()
    await expect(canvas).toHaveAttribute("data-scale", "1.00")
    await page.getByRole("button", { name: "Acercar" }).click()
    expect(Number(await canvas.getAttribute("data-scale"))).toBeGreaterThan(1.2)
    await canvas.dblclick({ position: { x: 300, y: 300 } })
    await expect(canvas).toHaveAttribute("data-scale", "1.00")
    await canvas.dblclick({ position: { x: 300, y: 300 } })
    expect(Number(await canvas.getAttribute("data-scale"))).toBeGreaterThan(2)
  })

  test("arrastrar mueve la página cuando está ampliada", async ({ page }) => {
    await askWithSegments(page)
    await assistant(page).getByTestId("citation-marker-1").click()
    const canvas = page.getByTestId("page-canvas")
    await page.getByRole("button", { name: "Acercar" }).click()
    await page.getByRole("button", { name: "Acercar" }).click()
    const mark = page.getByTestId("page-highlight")
    const before = await mark.boundingBox()
    await page.mouse.move(400, 400)
    await page.mouse.down()
    await page.mouse.move(340, 360, { steps: 4 })
    await page.mouse.up()
    const after = await mark.boundingBox()
    expect(after!.x).toBeLessThan(before!.x)
    expect(await canvas.getAttribute("data-scale")).not.toBe("1.00")
  })

  test("si el fragmento no se localiza lo dice y muestra la página sin marcar", async ({ page }) => {
    await mockBackend(page, {
      highlight: () => ({ page: 1, found: false, reason: "not_found" }),
      ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(TEXT, [CITATION, SECOND_CITATION], SEGMENTS)) }),
    })
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await assistant(page).getByTestId("citation-marker-1").click()
    const viewer = page.getByTestId("source-viewer")
    await expect(viewer.getByTestId("viewer-notice")).toContainText("No se encontró el fragmento")
    await expect(viewer.getByTestId("page-highlight")).toHaveCount(0)
    await expect(viewer.getByAltText("Página 1 de ACME-DEMO-DS")).toBeVisible()
  })

  test("una factura (imagen con OCR) no inventa posiciones: enseña el campo y lo explica", async ({ page }) => {
    const invoice = {
      chunk_id: "chunk-inv-1",
      quote: "importe_total: 537.94",
      doc: "F-2026-001",
      doc_id: "inv-123456789abc",
      section: "",
      pages: [1],
      fragment: "[F-2026-001 · factura] emisor: María Soler García; importe_total: 537.94",
    }
    await mockBackend(page, {
      ask: (route) =>
        route.fulfill({
          contentType: "text/event-stream",
          body: sse(answerEvents("El total es 537.94.", [invoice], [{ text: "El total es 537.94.", refs: [0] }])),
        }),
    })
    let highlightCalls = 0
    await page.route("**/api/sources/*/pages/*/highlight*", (route) => {
      highlightCalls += 1
      return route.abort()
    })
    await page.goto("/")
    await ask(page, "¿Total de la factura?")
    await assistant(page).getByTestId("citation-marker-1").click()
    const viewer = page.getByTestId("source-viewer")
    await expect(viewer.getByTestId("viewer-notice")).toContainText("OCR")
    await expect(viewer.getByTestId("viewer-fragment").locator("mark")).toHaveText("importe_total: 537.94")
    await expect(viewer.getByTestId("page-highlight")).toHaveCount(0)
    expect(highlightCalls).toBe(0)
  })

  test.describe("móvil", () => {
    test.use({ viewport: { width: 390, height: 844 } })
    test("el visor ocupa la pantalla y deja el detalle bajo la página", async ({ page }) => {
      await askWithSegments(page)
      await assistant(page).getByTestId("citation-marker-1").click()
      const viewer = page.getByTestId("source-viewer")
      const box = await viewer.boundingBox()
      expect(box!.width).toBeGreaterThanOrEqual(389)
      expect(box!.height).toBeGreaterThanOrEqual(843)
      await expect(viewer.getByTestId("viewer-fragment")).toBeVisible()
      await expect(viewer.getByTestId("page-canvas")).toBeVisible()
      const canvas = await viewer.getByTestId("page-canvas").boundingBox()
      expect(canvas!.height).toBeGreaterThan(300)
      await viewer.getByRole("button", { name: "Cerrar visor" }).click()
      await expect(viewer).toHaveCount(0)
    })
  })
})
