import AxeBuilder from "@axe-core/playwright"
import { readUIMessageStream } from "ai"
import { expect, test, type Page } from "@playwright/test"

import {
  answerEvents,
  ask,
  KEY_DATA_BLOCK,
  KEY_DATA_CITATIONS,
  KEY_DATA_FOLLOW_UPS,
  KEY_DATA_TEXT,
  mockBackend,
  sse,
  TABLE_BLOCK,
  TABLE_CITATIONS,
  TABLE_TEXT,
  type SseEvent,
} from "./mocks"
import { tableTsv, usableBlocks, usableFollowUps } from "../src/features/chat/lib/blocks"
import { ChunkMapper, type AskChunk } from "../src/features/chat/lib/chunks"
import { rehypeFigures } from "../src/features/chat/lib/figures"
import type { AskMessage, Block, StreamEvent } from "../src/features/chat/lib/types"
import { viewOfAssistant } from "../src/features/chat/lib/view"

type Hast = { type: string; value?: string; tagName?: string; properties?: Record<string, unknown>; children?: Hast[] }

function toHtml(node: Hast): string {
  if (node.type === "text") return node.value ?? ""
  const inner = (node.children ?? []).map(toHtml).join("")
  if (node.type !== "element") return inner
  const attrs = Object.entries(node.properties ?? {})
    .map(([key, value]) => ` ${key === "className" ? "class" : key}="${Array.isArray(value) ? value.join(" ") : String(value)}"`)
    .join("")
  return `<${node.tagName}${attrs}>${inner}</${node.tagName}>`
}

const keyDataEvents = () => answerEvents(KEY_DATA_TEXT, KEY_DATA_CITATIONS, [], { blocks: [KEY_DATA_BLOCK], follow_ups: KEY_DATA_FOLLOW_UPS })
const tableEvents = () => answerEvents(TABLE_TEXT, TABLE_CITATIONS, [], { blocks: [TABLE_BLOCK] })

async function answer(page: Page, events: () => SseEvent[], asked: (question: string) => SseEvent[] = () => answerEvents("Respuesta de seguimiento.")) {
  let first = true
  const backend = await mockBackend(page, {
    ask: (route, question) => {
      const body = first ? events() : asked(question)
      first = false
      return route.fulfill({ contentType: "text/event-stream", body: sse(body) })
    },
  })
  await page.goto("/")
  await ask(page, "¿Qué datos tiene la factura F-2026-001?")
  await expect(page.getByTestId("assistant-message").first()).toHaveAttribute("data-kind", "answer")
  return backend
}

test.describe("bloques: funciones puras", () => {
  test("se descartan los tipos desconocidos y las tablas descuadradas", () => {
    const unknown = { type: "chart", points: [] } as unknown as Block
    const ragged = { ...TABLE_BLOCK, rows: [{ ...TABLE_BLOCK.rows[0]!, cells: [TABLE_BLOCK.rows[0]!.cells[0]!] }] }
    expect(usableBlocks([unknown, KEY_DATA_BLOCK], KEY_DATA_CITATIONS)).toEqual([])
    expect(usableBlocks([ragged], TABLE_CITATIONS)).toEqual([])
    expect(usableBlocks([KEY_DATA_BLOCK], KEY_DATA_CITATIONS)).toEqual([KEY_DATA_BLOCK])
    expect(usableBlocks([TABLE_BLOCK], TABLE_CITATIONS)).toEqual([TABLE_BLOCK])
  })

  test("una cita ausente, ajena o con otro valor obliga a mostrar Markdown", () => {
    expect(usableBlocks([KEY_DATA_BLOCK], KEY_DATA_CITATIONS.slice(0, 2))).toEqual([])
    expect(usableBlocks([null], KEY_DATA_CITATIONS)).toEqual([])
    expect(usableBlocks([{ ...TABLE_BLOCK, columns: [null] }], TABLE_CITATIONS)).toEqual([])
    expect(usableBlocks([KEY_DATA_BLOCK], KEY_DATA_CITATIONS.map((citation) => ({ ...citation, quote: "incorrecto" })))).toEqual([])
  })

  test("las preguntas sugeridas vacías se descartan", () => {
    expect(usableFollowUps([{ label: "A", question: "  " }, ...KEY_DATA_FOLLOW_UPS])).toEqual(KEY_DATA_FOLLOW_UPS)
  })

  test("la tabla se copia como texto con tabuladores, con «—» donde no hay dato", () => {
    const row = TABLE_BLOCK.rows[0]!
    const withGap = { ...TABLE_BLOCK, rows: [{ ...row, cells: [row.cells[0]!, { text: null, kind: "date" as const, cite: null }, row.cells[2]!] }] }
    expect(tableTsv(withGap)).toBe("Factura\tfecha de emisión\timporte total\nF-2026-001\t—\t537,94 €\nTotal\t\t1.847,44 €")
  })

  test("el resaltado de cifras envuelve importes y fechas sin cambiar el texto", () => {
    const tree = {
      type: "root",
      children: [
        {
          type: "element",
          tagName: "p",
          properties: {},
          children: [
            { type: "text", value: "Total 1.706,60 € el 14/02/2026 y 2026-03-01." },
            { type: "element", tagName: "code", properties: {}, children: [{ type: "text", value: "9,99 €" }] },
          ],
        },
      ],
    }
    const before = JSON.stringify(tree).match(/"value":"([^"]*)"/g)?.map((value) => value.slice(9, -1)).join("")
    rehypeFigures()(tree)
    const html = toHtml(tree)
    expect(html).toContain('<span class="figure figure-amount" data-figure="amount">1.706,60 €</span>')
    expect(html).toContain('<span class="figure figure-date" data-figure="date">14/02/2026</span>')
    expect(html).toContain("<code>9,99 €</code>")
    expect(html.replace(/<[^>]+>/g, "")).toBe(before)
  })
})

async function viewOfStream(events: StreamEvent[]) {
  const mapper = new ChunkMapper()
  const chunks: AskChunk[] = events.flatMap((event) => mapper.push(event))
  const stream = new ReadableStream<AskChunk>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  })
  let message: AskMessage | undefined
  for await (const current of readUIMessageStream<AskMessage>({ stream })) message = current
  return viewOfAssistant(message as AskMessage, false)
}

const fromSse = (events: SseEvent[]) => events.map(([event, data]) => ({ event, ...data }) as unknown as StreamEvent)

test.describe("bloques: flujo del servicio", () => {
  test("el evento blocks llega al mensaje y done lo confirma", async () => {
    const view = await viewOfStream(fromSse(keyDataEvents()))
    expect(view.kind).toBe("answer")
    if (view.kind !== "answer") return
    expect(view.blocks).toEqual([KEY_DATA_BLOCK])
    expect(view.followUps).toEqual(KEY_DATA_FOLLOW_UPS)
  })

  test("un cliente que solo lee done también recibe los bloques", async () => {
    const view = await viewOfStream(fromSse(keyDataEvents()).filter((event) => event.event !== "blocks"))
    expect(view.kind === "answer" && view.blocks.length).toBe(1)
  })

  test("una respuesta sin bloques no los inventa", async () => {
    const view = await viewOfStream(fromSse(answerEvents()))
    expect(view.kind === "answer" && view.blocks).toEqual([])
  })
})

test.describe("bloques: datos clave", () => {
  test("cada dato sale con su etiqueta, su valor y su marcador de cita", async ({ page }) => {
    await answer(page, keyDataEvents)
    const card = page.getByTestId("key-data")
    await expect(card).toBeVisible()
    await expect(card.getByRole("heading", { name: "Datos clave" })).toBeVisible()
    for (const item of KEY_DATA_BLOCK.items) {
      const field = card.locator(`[data-field="${item.field}"]`)
      await expect(field.locator("dt")).toHaveText(item.label)
      await expect(field.locator("dd")).toContainText(item.text ?? "")
    }
    await expect(card.getByTestId("citation-marker-5")).toBeVisible()
    await expect(card).toContainText("Pendiente de revisión: F-2026-001")
    await expect(page.getByTestId("answer-text")).toHaveAttribute("data-structured", "true")
  })

  test("los importes van como cifras tabulares sin partirse", async ({ page }) => {
    await answer(page, keyDataEvents)
    const amount = page.getByTestId("key-data").locator('[data-figure="amount"]')
    await expect(amount).toHaveText("537,94 €")
    const style = await amount.evaluate((el) => {
      const css = getComputedStyle(el)
      return { numeric: css.fontVariantNumeric, wrap: css.whiteSpace }
    })
    expect(style.numeric).toContain("tabular-nums")
    expect(style.wrap).toBe("nowrap")
  })

  test("un marcador abre el visor de esa cita", async ({ page }) => {
    await answer(page, keyDataEvents)
    await page.getByTestId("key-data").getByTestId("citation-marker-5").click()
    await expect(page.getByTestId("source-viewer")).toBeVisible()
  })

  test("copiar los datos pone el texto de la tarjeta en el portapapeles", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await answer(page, keyDataEvents)
    await page.getByTestId("copy-key-data").click()
    const copied = await page.evaluate(() => navigator.clipboard.readText())
    expect(copied).toBe(
      ["Datos clave", "emisor: María Soler García", "cliente: Talleres Puig, S.A.", "número: F-2026-001", "fecha de emisión: 2026-01-01", "importe total: 537,94 €", "Pendiente de revisión: F-2026-001"].join("\n")
    )
  })

  test("las sugerencias se envían con clic y Alt+1 fuera del editor", async ({ page }) => {
    const backend = await answer(page, keyDataEvents)
    const chips = page.getByTestId("follow-up")
    await expect(chips).toHaveText(["Fecha de vencimiento", "Cuota de IVA"])
    await expect(chips.first()).toHaveAttribute("aria-keyshortcuts", "Alt+1")
    await page.getByLabel("Pregunta", { exact: true }).blur()
    await page.keyboard.press("Alt+1")
    await expect.poll(() => backend.questions.at(-1)).toBe(KEY_DATA_FOLLOW_UPS[0]!.question)
    await expect(page.getByTestId("assistant-message")).toHaveCount(2)
    await page.getByTestId("follow-up").last().click()
    await expect.poll(() => backend.questions.at(-1)).toBe(KEY_DATA_FOLLOW_UPS[1]!.question)
  })

  test("Option no intercepta copiar ni sugerencias al escribir", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    const backend = await answer(page, keyDataEvents)
    await page.evaluate(() => navigator.clipboard.writeText("conservar"))
    await page.getByLabel("Pregunta", { exact: true }).focus()
    for (const code of ["KeyC", "KeyT", "Digit1"]) {
      const prevented = await page.getByLabel("Pregunta", { exact: true }).evaluate((element, code) => {
        const event = new KeyboardEvent("keydown", { code, altKey: true, bubbles: true, cancelable: true })
        element.dispatchEvent(event)
        return event.defaultPrevented
      }, code)
      expect(prevented).toBe(false)
    }
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe("conservar")
    expect(backend.questions).toHaveLength(1)
  })
})

test.describe("bloques: tabla", () => {
  test("la tabla enseña cabeceras, filas, el total y la nota", async ({ page }) => {
    await answer(page, tableEvents)
    const table = page.getByTestId("data-table")
    await expect(table.getByRole("columnheader")).toHaveText(["Factura", "fecha de emisión", "importe total"])
    await expect(table.getByRole("row")).toHaveCount(5)
    await expect(table.getByTestId("table-summary").locator("[data-figure]")).toHaveText("1.847,44 €")
    await expect(table.getByRole("cell").filter({ has: page.locator('[data-figure="amount"]') }).filter({ hasText: "1.210,00 €" })).toBeVisible()
    await expect(table.getByTestId("citation-marker-4")).toBeVisible()
  })

  test("las cifras de una columna de importes se alinean a la derecha", async ({ page }) => {
    await answer(page, tableEvents)
    const cells = page.getByTestId("data-table").locator("tbody tr td:last-child")
    const rights = await cells.evaluateAll((els) => els.map((el) => Math.round(el.querySelector("[data-figure]")!.getBoundingClientRect().right)))
    expect(new Set(rights).size).toBe(1)
  })

  test("el número de factura de una fila pregunta por esa factura", async ({ page }) => {
    const backend = await answer(page, tableEvents)
    await page.getByTestId("row-ask").nth(1).click()
    await expect.poll(() => backend.questions.at(-1)).toBe("¿Qué datos tiene la factura F-2026-002?")
  })

  test("copiar la tabla da texto con tabuladores, también con Alt+T; Alt+C copia la respuesta", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await answer(page, tableEvents)
    const tsv = tableTsv(TABLE_BLOCK)
    await page.getByTestId("copy-table").click()
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(tsv)
    await page.evaluate(() => navigator.clipboard.writeText(""))
    await page.keyboard.press("Alt+T")
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(tsv)
    await page.keyboard.press("Alt+C")
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain("Facturas de Talleres Puig, S.A.:")
  })

  test("Alt+T avisa cuando la respuesta no tiene tabla", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await answer(page, keyDataEvents)
    await page.getByLabel("Pregunta", { exact: true }).blur()
    await page.keyboard.press("Alt+T")
    await expect(page.getByText("Esta respuesta no tiene tabla")).toBeVisible()
  })
})

test.describe("bloques: degradación", () => {
  test("un bloque desconocido deja el texto Markdown de la respuesta", async ({ page }) => {
    const unknown = { type: "chart", points: [] } as unknown as Block
    await answer(page, () => answerEvents("Factura F-2026-001: importe total: 537,94 €", KEY_DATA_CITATIONS, [], { blocks: [unknown] }))
    await expect(page.getByTestId("answer-text")).toHaveAttribute("data-structured", "false")
    await expect(page.getByTestId("answer-text")).toContainText("Factura F-2026-001: importe total: 537,94 €")
    await expect(page.getByTestId("key-data")).toHaveCount(0)
  })

  test("done con versión desconocida descarta los bloques anticipados", async ({ page }) => {
    await answer(page, () => keyDataEvents().map(([name, data]) => [name, name === "done" ? { ...data, blocks_version: 2 } : data]))
    await expect(page.getByTestId("answer-text")).toHaveAttribute("data-structured", "false")
    await expect(page.getByTestId("answer-text")).toContainText("537,94 €")
  })

  test("las cifras de un texto Markdown se resaltan sin cambiar lo que dice", async ({ page }) => {
    await answer(page, () => answerEvents("El total es 1.706,60 € el 14/02/2026."))
    const text = page.getByTestId("answer-text")
    await expect(text.locator('[data-figure="amount"]')).toHaveText("1.706,60 €")
    await expect(text.locator('[data-figure="date"]')).toHaveText("14/02/2026")
    await expect(text).toHaveText(/El total es 1\.706,60 € el 14\/02\/2026\./)
  })
})

test.describe("bloques: esperas y movimiento", () => {
  test("mientras llega la respuesta hay un esqueleto, y desaparece con ella", async ({ page }) => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    await mockBackend(page, {
      ask: async (route) => {
        await gate
        await route.fulfill({ contentType: "text/event-stream", body: sse(keyDataEvents()) })
      },
    })
    await page.goto("/")
    await ask(page, "¿Qué datos tiene la factura F-2026-001?")
    await expect(page.getByTestId("answer-skeleton")).toBeVisible()
    release()
    await expect(page.getByTestId("key-data")).toBeVisible()
    await expect(page.getByTestId("answer-skeleton")).toHaveCount(0)
  })

  test("con movimiento reducido el esqueleto no se anima", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" })
    await mockBackend(page, { ask: () => new Promise(() => undefined) })
    await page.goto("/")
    await ask(page, "¿Qué datos tiene la factura F-2026-001?")
    const line = page.getByTestId("answer-skeleton").locator('[data-slot="skeleton"]').first()
    await expect(line).toBeVisible()
    const duration = await line.evaluate((el) => parseFloat(getComputedStyle(el).animationDuration))
    expect(duration).toBeLessThan(0.001)
  })
})

test.describe("bloques: accesibilidad", () => {
  for (const [name, events] of [["datos clave", keyDataEvents], ["tabla", tableEvents]] as const) {
    for (const theme of ["industrial", "neutral"] as const) {
      for (const dark of [false, true]) {
        test(`${name} sin violaciones serias (${theme} ${dark ? "oscuro" : "claro"})`, async ({ page }) => {
          await page.addInitScript(
            ([t, d]) => {
              localStorage.setItem("doc-assistant.theme", t)
              localStorage.setItem("doc-assistant.mode", d ? "dark" : "light")
            },
            [theme, dark] as const
          )
          await answer(page, events)
          await page.mouse.move(0, 0)
          const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()
          const serious = results.violations.filter((item) => item.impact === "serious" || item.impact === "critical")
          expect(serious, JSON.stringify(serious.map((item) => ({ id: item.id, nodes: item.nodes.map((n) => n.html) })), null, 2)).toEqual([])
        })
      }
    }
  }
})
