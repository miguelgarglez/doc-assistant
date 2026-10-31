import { expect, test, type Page } from "@playwright/test"

import {
  answerEvents,
  ask,
  CITATION,
  composer,
  mockBackend,
  refusalEvents,
  SECOND_CITATION,
  sse,
} from "./mocks"

const assistant = (page: Page) => page.getByTestId("assistant-message")

test.describe("chat", () => {
  test("estado vacío: sugerencias reales, composer anclado y sin scroll de página", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    const empty = page.getByTestId("chat-empty")
    await expect(empty).toBeVisible()
    await expect(empty.getByRole("button", { name: /¿De qué trata Ficha técnica de la pinza GR-50\?/ })).toBeVisible()
    await expect(page.getByTestId("send-ask")).toBeDisabled()
    const overflow = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
    expect(overflow).toBeLessThanOrEqual(0)
  })

  test("estado vacío sin fuentes ofrece añadirlas", async ({ page }) => {
    await mockBackend(page, { sources: [] })
    await page.goto("/")
    await expect(page.getByTestId("empty-add-source")).toBeVisible()
    await expect(page.getByTestId("chat-empty").getByRole("button", { name: /¿De qué trata/ })).toHaveCount(0)
  })

  test("una sugerencia envía la pregunta", async ({ page }) => {
    const { questions } = await mockBackend(page)
    await page.goto("/")
    await page.getByRole("button", { name: /¿De qué trata Ficha técnica/ }).click()
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    expect(questions).toEqual(["¿De qué trata Ficha técnica de la pinza GR-50?"])
  })

  test("respuesta con Markdown, pasos colapsados y citas numeradas que abren el visor", async ({ page }) => {
    await mockBackend(page, {
      ask: (route) =>
        route.fulfill({
          contentType: "text/event-stream",
          body: sse(answerEvents("La carga útil es **12 kg**:\n\n- ISO 9409-1\n- IP54", [CITATION, SECOND_CITATION])),
        }),
    })
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    const message = assistant(page)
    await expect(message).toHaveAttribute("data-kind", "answer")
    await expect(message.getByText("12 kg", { exact: true })).toBeVisible()
    await expect(message.getByRole("listitem")).toHaveCount(2)
    await expect(page.getByTestId("trace")).toContainText("3 pasos")
    await expect(page.getByTestId("citation-1")).toBeVisible()
    await expect(page.getByTestId("citation-2")).toBeVisible()
    await expect(page.getByTestId("source-viewer")).toHaveCount(0)

    await page.getByTestId("citation-1").click()
    const viewer = page.getByTestId("source-viewer")
    await expect(viewer).toBeVisible()
    await expect(viewer.getByTestId("viewer-fragment").locator("mark")).toHaveText("Carga útil máxima: 12 kg")
    await expect(viewer.getByTestId("viewer-fragment")).not.toContainText("pdf-acme-demo-ds ·")
    await expect(viewer.getByAltText("Página 1 de ACME-DEMO-DS")).toBeVisible()

    await viewer.getByRole("button", { name: "Cita siguiente" }).click()
    await expect(viewer.getByTestId("viewer-fragment").locator("mark")).toHaveText("ISO 9409-1-50-4-M6")

    await page.keyboard.press("Escape")
    await expect(viewer).toHaveCount(0)
  })

  test("el texto provisional se ve sin verificar y se retira en un rechazo", async ({ page }) => {
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => (release = resolve))
    await mockBackend(page, {
      ask: async (route) => {
        await gate
        await route.fulfill({ contentType: "text/event-stream", body: sse(refusalEvents("Texto sin verificar")) })
      },
    })
    await page.goto("/")
    await ask(page, "Pregunta sin respaldo")
    await expect(page.getByText("Buscando en las fuentes…")).toBeVisible()
    release()
    await expect(assistant(page)).toHaveAttribute("data-kind", "refusal")
    await expect(page.getByTestId("refusal-notice")).toContainText("No dispongo de esa información")
    await expect(page.getByText("Texto sin verificar")).toHaveCount(0)
    await expect(page.getByTestId("provisional-answer")).toHaveCount(0)
    await expect(page.getByTestId("refusal-notice").getByRole("button", { name: /ACME-DEMO-DS · 3 Dimensiones/ })).toBeVisible()
  })

  test("un apartado relacionado de un rechazo lanza una pregunta nueva", async ({ page }) => {
    const { questions } = await mockBackend(page, {
      ask: (route, question) =>
        route.fulfill({
          contentType: "text/event-stream",
          body: sse(question.includes("Dimensiones") ? answerEvents("120 x 80 mm.") : refusalEvents()),
        }),
    })
    await page.goto("/")
    await ask(page, "¿Cuánto pesa?")
    await page.getByRole("button", { name: /ACME-DEMO-DS · 3 Dimensiones/ }).click()
    await expect(assistant(page).nth(1)).toHaveAttribute("data-kind", "answer")
    expect(questions.at(-1)).toBe("¿Qué dice ACME-DEMO-DS sobre Dimensiones?")
  })

  test("detener muestra la respuesta como detenida y permite reintentar", async ({ page }) => {
    let calls = 0
    await mockBackend(page, {
      ask: async (route) => {
        calls += 1
        if (calls === 1) return new Promise(() => undefined)
        await route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents()) })
      },
    })
    await page.goto("/")
    await ask(page, "Pregunta lenta")
    await page.getByTestId("cancel-ask").click()
    await expect(page.getByTestId("ask-cancelled")).toBeVisible()
    await expect(page.getByTestId("send-ask")).toBeVisible()
    await page.getByTestId("ask-cancelled").getByRole("button", { name: "Reintentar" }).click()
    await expect(assistant(page).last()).toHaveAttribute("data-kind", "answer")
    expect(calls).toBe(2)
  })

  test("Esc detiene la generación", async ({ page }) => {
    await mockBackend(page, { ask: () => new Promise(() => undefined) })
    await page.goto("/")
    await ask(page, "Pregunta lenta")
    await expect(page.getByTestId("cancel-ask")).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByTestId("ask-cancelled")).toBeVisible()
  })

  test("un error del servicio se explica y se puede reintentar", async ({ page }) => {
    let calls = 0
    await mockBackend(page, {
      ask: async (route) => {
        calls += 1
        if (calls === 1) {
          await route.fulfill({ status: 502, json: { code: "adapter_error", message: "El modelo no está disponible." } })
          return
        }
        await route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents()) })
      },
    })
    await page.goto("/")
    await ask(page, "Pregunta")
    const alert = page.getByTestId("ask-error-notice")
    await expect(alert).toContainText("El modelo no está disponible.")
    await alert.getByRole("button", { name: "Reintentar" }).click()
    await expect(assistant(page).last()).toHaveAttribute("data-kind", "answer")
  })

  test("un stream cortado sin done no se presenta como respuesta", async ({ page }) => {
    await mockBackend(page, {
      ask: (route) =>
        route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents().slice(0, 4)) }),
    })
    await page.goto("/")
    await ask(page, "Pregunta")
    await expect(page.getByTestId("ask-error-notice")).toBeVisible()
    await expect(page.getByTestId("answer-text")).toHaveCount(0)
  })

  test("sin /ask/stream usa /ask", async ({ page }) => {
    await mockBackend(page, { ask: (route) => route.fulfill({ status: 404, json: { code: "not_found", message: "no" } }) })
    await page.route("**/api/ask", (route) =>
      route.fulfill({
        json: { ok: true, answer: "Respuesta sin streaming.", citations: [CITATION], reason: "", suggestions: [], timings: { total: 1 } },
      })
    )
    await page.goto("/")
    await ask(page, "Pregunta")
    await expect(page.getByTestId("answer-text")).toContainText("Respuesta sin streaming.")
    await expect(page.getByTestId("citation-1")).toBeVisible()
  })

  test("copiar y volver a generar", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    const { questions } = await mockBackend(page)
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    await page.getByTestId("copy-answer").click()
    await expect(page.getByTestId("copy-answer")).toHaveAccessibleName("Copiado")
    const copied = await page.evaluate(() => navigator.clipboard.readText())
    expect(copied).toContain("La carga útil máxima es de 12 kg.")
    expect(copied).toContain("ACME-DEMO-DS")
    await page.getByTestId("regenerate").click()
    await expect(page.getByTestId("assistant-message")).toHaveCount(1)
    await expect.poll(() => questions.length).toBe(2)
    expect(questions).toEqual(["¿Carga útil?", "¿Carga útil?"])
  })

  test("teclado: Shift+Enter, Enter, historial con ↑/↓ y composición IME", async ({ page }) => {
    const { questions } = await mockBackend(page)
    await page.goto("/")
    const input = composer(page)
    await input.fill("línea 1")
    await input.press("Shift+Enter")
    await input.type("línea 2")
    await expect(input).toHaveValue("línea 1\nlínea 2")

    await input.evaluate((el) => {
      el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", isComposing: true, bubbles: true, cancelable: true }))
    })
    expect(questions).toHaveLength(0)
    await expect(input).toHaveValue("línea 1\nlínea 2")

    await input.press("Enter")
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    expect(questions).toEqual(["línea 1\nlínea 2"])
    await expect(input).toHaveValue("")

    await ask(page, "segunda")
    await expect(assistant(page)).toHaveCount(2)
    await input.press("ArrowUp")
    await expect(input).toHaveValue("segunda")
    await input.press("ArrowUp")
    await expect(input).toHaveValue("línea 1\nlínea 2")
    await input.press("ArrowDown")
    await expect(input).toHaveValue("segunda")
    await input.press("ArrowDown")
    await expect(input).toHaveValue("")
  })

  test("Cmd/Ctrl+K enfoca el campo y ? abre la ayuda de atajos", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await page.getByRole("link", { name: "Fuentes" }).click()
    await page.keyboard.press("Control+k")
    await expect(page).toHaveURL(/\/$/)
    await expect(composer(page)).toBeFocused()
    await page.locator("body").click({ position: { x: 600, y: 300 } })
    await page.keyboard.press("?")
    await expect(page.getByTestId("shortcuts-help")).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByTestId("shortcuts-help")).toHaveCount(0)
  })

  test("la conversación sobrevive a un cambio de ruta y a recargar; nueva conversación la limpia", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await ask(page, "¿Carga útil?")
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    await page.getByRole("link", { name: "Sistema" }).click()
    await expect(page).toHaveURL(/\/sistema$/)
    await page.getByRole("link", { name: "Chat" }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(assistant(page)).toBeVisible()
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    await page.reload()
    await expect(page.getByTestId("user-message")).toContainText("¿Carga útil?")
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    await page.getByTestId("new-conversation").click()
    await expect(page.getByTestId("chat-empty")).toBeVisible()
  })

  test("el hilo es el único scroll: la página no se desplaza y hay botón para ir al final", async ({ page }) => {
    await mockBackend(page, {
      ask: (route) =>
        route.fulfill({
          contentType: "text/event-stream",
          body: sse(answerEvents("Un párrafo largo de respuesta. ".repeat(20))),
        }),
    })
    await page.goto("/")
    for (let i = 0; i < 6; i += 1) {
      await ask(page, `Pregunta número ${i + 1}`)
      await expect(assistant(page)).toHaveCount(i + 1)
      await expect(assistant(page).last()).toHaveAttribute("data-kind", "answer")
    }
    const metrics = await page.evaluate(() => {
      const scroller = document.querySelector('[role="log"]')!.firstElementChild as HTMLElement
      return {
        pageOverflow: document.documentElement.scrollHeight - window.innerHeight,
        threadScrolls: scroller.scrollHeight > scroller.clientHeight,
        composerBottom: document.querySelector('[data-testid="composer"]')!.getBoundingClientRect().bottom,
        innerHeight: window.innerHeight,
      }
    })
    expect(metrics.pageOverflow).toBeLessThanOrEqual(0)
    expect(metrics.threadScrolls).toBe(true)
    expect(metrics.composerBottom).toBeLessThanOrEqual(metrics.innerHeight)
    await page.getByRole("log").hover()
    await page.mouse.wheel(0, -10_000)
    await expect(page.getByRole("button", { name: "Ir al final" })).toBeVisible()
    await page.getByRole("button", { name: "Ir al final" }).click()
    await expect(page.getByRole("button", { name: "Ir al final" })).toHaveCount(0)
  })
})

test.describe("adjuntos en el composer", () => {
  const pasteFile = (page: Page, name: string, type: string) =>
    composer(page).evaluate(
      (el, [fileName, mime]) => {
        const data = new DataTransfer()
        data.items.add(new File(["%PDF-1.4 demo"], fileName as string, { type: mime as string }))
        el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }))
      },
      [name, type]
    )

  test("pegar un PDF lo sube como fuente, muestra su estado y se adjunta al mensaje", async ({ page }) => {
    await mockBackend(page)
    let uploaded = 0
    await page.route("**/api/documents", async (route) => {
      uploaded += 1
      await new Promise((resolve) => setTimeout(resolve, 400))
      await route.fulfill({
        json: { n_chunks: 5, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-x", path: "x", content_hash: "h", created: true },
      })
    })
    await page.goto("/")
    await pasteFile(page, "manual.pdf", "application/pdf")
    const chip = page.getByRole("list", { name: "Archivos adjuntos" }).getByRole("listitem")
    await expect(chip).toContainText("manual.pdf")
    await expect(chip).toHaveAttribute("data-status", /uploading|processing/)
    await composer(page).fill("¿Qué dice el manual?")
    await expect(page.getByTestId("send-ask")).toBeDisabled()
    await expect(chip).toHaveAttribute("data-status", "done")
    await expect(page.getByTestId("send-ask")).toBeEnabled()
    await composer(page).press("Enter")
    await expect(page.getByTestId("user-message")).toContainText("manual.pdf")
    await expect(page.getByRole("list", { name: "Archivos adjuntos" })).toHaveCount(0)
    expect(uploaded).toBe(1)
  })

  test("un tipo no admitido falla a la vista y se puede quitar", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await pasteFile(page, "notas.txt", "text/plain")
    const chip = page.getByRole("list", { name: "Archivos adjuntos" }).getByRole("listitem")
    await expect(chip).toHaveAttribute("data-status", "error")
    await expect(chip).toContainText("Solo se admiten PDF e imágenes")
    await chip.getByRole("button", { name: "Quitar notas.txt" }).click()
    await expect(chip).toHaveCount(0)
  })

  test("arrastrar un archivo a la ventana muestra la zona de suelta y lo añade", async ({ page }) => {
    await mockBackend(page)
    await page.route("**/api/documents", (route) =>
      route.fulfill({
        json: { n_chunks: 2, chunk_ids: [], warnings: [], timings: {}, doc_id: "pdf-y", path: "y", content_hash: "h", created: true },
      })
    )
    await page.goto("/")
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "0")
    const files = async (type: "dragenter" | "drop") =>
      page.evaluate((kind) => {
        const data = new DataTransfer()
        data.items.add(new File(["%PDF-1.4"], "arrastrado.pdf", { type: "application/pdf" }))
        document.body.dispatchEvent(new DragEvent(kind, { dataTransfer: data, bubbles: true, cancelable: true }))
      }, type)
    await files("dragenter")
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "1")
    await files("drop")
    await expect(page.getByTestId("drop-overlay")).toHaveCSS("opacity", "0")
    await expect(page.getByRole("list", { name: "Archivos adjuntos" })).toContainText("arrastrado.pdf")
  })
})

test.describe("sin scroll de página en escritorio", () => {
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1280, height: 720 },
  ]) {
    test(`${viewport.width}x${viewport.height}: chat con respuesta y visor abiertos`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await mockBackend(page)
      await page.goto("/")
      await ask(page, "¿Carga útil?")
      await page.getByTestId("citation-1").click()
      await expect(page.getByTestId("source-viewer")).toBeVisible()
      const metrics = await page.evaluate(() => ({
        overflow: document.documentElement.scrollHeight - window.innerHeight,
        composer: document.querySelector('[data-testid="composer"]')!.getBoundingClientRect().bottom,
        sidebar: document.querySelector('[data-slot="sidebar-container"]')!.getBoundingClientRect().height,
        inner: window.innerHeight,
      }))
      expect(metrics.overflow).toBeLessThanOrEqual(0)
      expect(metrics.composer).toBeLessThanOrEqual(metrics.inner)
      expect(metrics.sidebar).toBe(metrics.inner)
    })
  }
})

test.describe("móvil", () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test("menú plegable, composer usable y visor en hoja inferior", async ({ page }) => {
    await mockBackend(page)
    await page.goto("/")
    await expect(page.locator('[data-slot="sidebar-container"]')).toBeHidden()
    await page.getByRole("button", { name: "Abrir el menú" }).click()
    await expect(page.getByRole("link", { name: "Fuentes" })).toBeVisible()
    await page.getByRole("link", { name: "Chat" }).click()
    await expect(page.getByRole("link", { name: "Fuentes" })).toBeHidden()

    await ask(page, "¿Carga útil?")
    await expect(assistant(page)).toHaveAttribute("data-kind", "answer")
    const box = await page.getByTestId("composer").boundingBox()
    expect(box!.y + box!.height).toBeLessThanOrEqual(844)
    expect(box!.width).toBeGreaterThan(300)

    await page.getByTestId("citation-1").click()
    const viewer = page.getByTestId("source-viewer")
    await expect(viewer).toBeVisible()
    const sheet = await viewer.boundingBox()
    expect(sheet!.y).toBeGreaterThan(80)
    await viewer.getByRole("button", { name: "Cerrar visor" }).click()
    await expect(viewer).toHaveCount(0)
  })
})
