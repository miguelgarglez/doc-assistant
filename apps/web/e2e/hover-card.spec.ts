import { expect, test, type Page } from "@playwright/test"

import { answerEvents, ask, CITATION, mockBackend, SECOND_CITATION, sse, type Segment } from "./mocks"

const TEXT = "La carga útil máxima es de 12 kg. La interfaz de brida es ISO 9409-1-50-4-M6."
const SEGMENTS: Segment[] = [
  { text: "La carga útil máxima es de 12 kg.", refs: [0] },
  { text: " La interfaz de brida es ISO 9409-1-50-4-M6.", refs: [1] },
]
const CARD = '[data-slot="hover-card-content"]'

const LONG_QUOTE =
  "Carga útil máxima: 12 kg, medida con el centro de gravedad a 40 mm de la brida, a velocidad nominal y con la herramienta montada en posición vertical."

async function thread(page: Page, answers: number, segments: Segment[] = SEGMENTS, quote?: string) {
  const second = quote ? { ...SECOND_CITATION, quote } : SECOND_CITATION
  await mockBackend(page, {
    ask: (route) =>
      route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(TEXT, [CITATION, second], segments)) }),
  })
  await page.goto("/")
  for (let i = 0; i < answers; i++) {
    await ask(page, `Pregunta ${i + 1}`)
    await expect(page.getByTestId("assistant-message").nth(i)).toHaveAttribute("data-kind", "answer")
  }
}

type Rect = { x: number; y: number; width: number; height: number }

async function geometry(page: Page, marker: string, nth = -1) {
  return page.evaluate(
    ([markerId, cardSelector, position]) => {
      const markers = document.querySelectorAll(`[data-testid="${markerId}"]`)
      const anchor = markers[position < 0 ? markers.length + position : position]
      const card = document.querySelector(cardSelector)
      if (!anchor || !card) return null
      const rect = (element: Element): Rect => {
        const { x, y, width, height } = element.getBoundingClientRect()
        return { x, y, width, height }
      }
      const [originX = 0, originY = 0] = getComputedStyle(card)
        .transformOrigin.split(" ")
        .map((value) => Number.parseFloat(value))
      return { marker: rect(anchor), card: rect(card), origin: { x: originX, y: originY }, transform: getComputedStyle(card).transform }
    },
    [marker, CARD, nth] as const
  )
}

async function settled(page: Page, marker: string, nth = -1) {
  await expect.poll(async () => (await geometry(page, marker, nth))?.transform).toBe("none")
  const found = await geometry(page, marker, nth)
  if (!found) throw new Error("no card")
  return found
}

const centerX = (rect: Rect) => rect.x + rect.width / 2
const bottom = (rect: Rect) => rect.y + rect.height

async function frames(page: Page) {
  return page.evaluate(() => {
    let scroller: HTMLElement | null = document.querySelector<HTMLElement>('[data-testid="thread"]')
    while (scroller && scroller.scrollHeight <= scroller.clientHeight + 1) scroller = scroller.parentElement
    const composer = document.querySelector('[data-testid="composer"]')
    if (!scroller || !composer) throw new Error("sin hilo o composer")
    const rect = (element: Element): Rect => {
      const { x, y, width, height } = element.getBoundingClientRect()
      return { x, y, width, height }
    }
    return { thread: rect(scroller), composer: rect(composer) }
  })
}

test.describe("vista previa de la cita inline", () => {
  test("se centra en su marcador y nace de él", async ({ page }) => {
    await thread(page, 1)
    await page.getByTestId("citation-marker-1").hover()
    const { marker, card, origin } = await settled(page, "citation-marker-1")
    expect(Math.abs(centerX(card) - centerX(marker))).toBeLessThanOrEqual(1)
    const below = card.y > marker.y
    const gap = below ? card.y - (marker.y + marker.height) : marker.y - (card.y + card.height)
    expect(gap).toBeGreaterThanOrEqual(4)
    expect(gap).toBeLessThanOrEqual(8)
    expect(Math.abs(origin.x - (centerX(marker) - card.x))).toBeLessThanOrEqual(1.5)
    expect(Math.abs(origin.y - (below ? -gap : card.height + gap))).toBeLessThanOrEqual(1.5)
  })

  test("junto al borde de la ventana se desplaza pero no se sale ni pierde el marcador", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 800 })
    await thread(page, 1)
    await page.getByTestId("citation-marker-2").focus()
    const { marker, card } = await settled(page, "citation-marker-2")
    expect(card.x).toBeGreaterThanOrEqual(0)
    expect(card.x + card.width).toBeLessThanOrEqual(390)
    expect(centerX(marker)).toBeGreaterThan(card.x)
    expect(centerX(marker)).toBeLessThan(card.x + card.width)
  })

  test("acompaña al marcador mientras se desplaza el hilo", async ({ page }) => {
    await thread(page, 6)
    const scroller = await page.getByTestId("thread").evaluateHandle((node) => {
      let element: HTMLElement | null = node as HTMLElement
      while (element && element.scrollHeight <= element.clientHeight + 1) element = element.parentElement
      return element
    })
    await expect.poll(() => scroller.evaluate((el) => (el as HTMLElement).scrollTop)).toBeGreaterThan(0)
    await page.waitForTimeout(700)
    await page.getByTestId("citation-marker-1").nth(3).hover()
    const start = await settled(page, "citation-marker-1", 3)
    const offsetY = start.card.y - start.marker.y
    const offsetX = centerX(start.card) - centerX(start.marker)
    for (const step of [3, 3, 3]) {
      await scroller.evaluate((el, by) => ((el as HTMLElement).scrollTop -= by), step)
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      const now = await geometry(page, "citation-marker-1", 3)
      expect(now, "la tarjeta sigue abierta").not.toBeNull()
      if (!now) return
      expect(Math.abs(now.card.y - now.marker.y - offsetY)).toBeLessThanOrEqual(1)
      expect(Math.abs(centerX(now.card) - centerX(now.marker) - offsetX)).toBeLessThanOrEqual(1)
    }
  })

  test("si el marcador sale del hilo, la tarjeta no queda flotando sola", async ({ page }) => {
    await thread(page, 6)
    await page.waitForTimeout(700)
    await page.getByTestId("citation-marker-1").last().focus()
    await expect(page.locator(CARD)).toBeVisible()
    await page.getByTestId("thread").evaluate((node) => {
      let element: HTMLElement | null = node as HTMLElement
      while (element && element.scrollHeight <= element.clientHeight + 1) element = element.parentElement
      if (element) element.scrollTop = 0
    })
    await expect(page.locator(CARD)).toBeHidden()
  })

  for (const [name, segments, marker] of [
    ["marcador inline", SEGMENTS, "citation-marker-2"],
    ["pastilla bajo la respuesta", [], "citation-2"],
  ] as const) {
    test(`${name} al final del hilo: abre hacia arriba, sin solapar el composer`, async ({ page }) => {
      await thread(page, 6, [...segments], LONG_QUOTE)
      await page.waitForTimeout(700)
      await page.getByTestId(marker).last().hover()
      const { marker: anchor, card } = await settled(page, marker)
      const { thread: area, composer: box } = await frames(page)
      expect(bottom(card), "la tarjeta termina antes del composer").toBeLessThanOrEqual(box.y)
      expect(bottom(card), "y dentro del hilo").toBeLessThanOrEqual(bottom(area))
      expect(card.y, "abre hacia arriba").toBeLessThan(anchor.y)
      expect(Math.abs(centerX(card) - centerX(anchor)), "sigue centrada en el marcador").toBeLessThanOrEqual(1)
    })
  }

  test("con el hilo más bajo que la tarjeta, la tarjeta se ciñe al hilo y no toca el composer", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 300 })
    await thread(page, 6, SEGMENTS, LONG_QUOTE)
    await page.waitForTimeout(700)
    await page.getByTestId("citation-marker-2").last().hover()
    const { card } = await settled(page, "citation-marker-2")
    const { thread: area, composer: box } = await frames(page)
    const natural = await page.locator(CARD).evaluate((node) => node.scrollHeight)
    expect(natural, "el contenido no cabe en el hilo con su margen").toBeGreaterThan(area.height - 24)
    expect(bottom(card)).toBeLessThanOrEqual(box.y)
    expect(card.y).toBeGreaterThanOrEqual(area.y)
  })
})
