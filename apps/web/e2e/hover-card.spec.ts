import { expect, test, type Page } from "@playwright/test"

import { answerEvents, ask, CITATION, mockBackend, SECOND_CITATION, sse, type Segment } from "./mocks"

const TEXT = "La carga útil máxima es de 12 kg. La interfaz de brida es ISO 9409-1-50-4-M6."
const SEGMENTS: Segment[] = [
  { text: "La carga útil máxima es de 12 kg.", refs: [0] },
  { text: " La interfaz de brida es ISO 9409-1-50-4-M6.", refs: [1] },
]
const CARD = '[data-slot="hover-card-content"]'

async function thread(page: Page, answers: number) {
  await mockBackend(page, {
    ask: (route) =>
      route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents(TEXT, [CITATION, SECOND_CITATION], SEGMENTS)) }),
  })
  await page.goto("/")
  for (let i = 0; i < answers; i++) {
    await ask(page, `Pregunta ${i + 1}`)
    await expect(page.getByTestId("assistant-message").nth(i)).toHaveAttribute("data-kind", "answer")
  }
}

type Rect = { x: number; y: number; width: number; height: number }

async function geometry(page: Page, marker: string) {
  return page.evaluate(
    ([markerId, cardSelector]) => {
      const markers = document.querySelectorAll(`[data-testid="${markerId}"]`)
      const anchor = markers[markers.length - 1]
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
    [marker, CARD] as const
  )
}

async function settled(page: Page, marker: string) {
  await expect.poll(async () => (await geometry(page, marker))?.transform).toBe("none")
  const found = await geometry(page, marker)
  if (!found) throw new Error("no card")
  return found
}

const centerX = (rect: Rect) => rect.x + rect.width / 2

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
    await page.getByTestId("citation-marker-1").last().hover()
    const start = await settled(page, "citation-marker-1")
    const offsetY = start.card.y - start.marker.y
    const offsetX = centerX(start.card) - centerX(start.marker)
    for (const step of [3, 3, 3]) {
      await scroller.evaluate((el, by) => ((el as HTMLElement).scrollTop -= by), step)
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      const now = await geometry(page, "citation-marker-1")
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
})
