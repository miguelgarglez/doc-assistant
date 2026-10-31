import { expect, test } from "@playwright/test"

import { answerEvents, ask, CLARIFICATION, clarificationEvents, mockBackend, sse } from "./mocks"
import { candidateName, candidateParties, candidateTotal, hiddenCandidates } from "../src/lib/chat/clarification"

const QUESTION = "¿Cuál es el importe total de la factura?"
const card = (page: import("@playwright/test").Page) => page.getByTestId("clarification-notice")

async function askAmbiguous(page: import("@playwright/test").Page, clarification = CLARIFICATION) {
  const backend = await mockBackend(page, {
    ask: (route, question) =>
      route.fulfill({
        contentType: "text/event-stream",
        body: sse(question === QUESTION ? clarificationEvents(clarification) : answerEvents("El importe total es 1.210,00 €.")),
      }),
  })
  await page.goto("/")
  await ask(page, QUESTION)
  await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-kind", "clarification")
  return backend
}

test.describe("aclaración: funciones puras", () => {
  const [full, bare] = CLARIFICATION.candidates

  test("una candidata muestra solo los datos que tiene la factura", () => {
    expect(candidateParties(full)).toBe("De Suministros Aranda, S.L. para Taller Norte, S.L.")
    expect(candidateTotal(full)).toBe("1.210,00 €")
    expect(candidateParties(bare)).toBe("De Clara Ibáñez Roca")
    expect(candidateTotal(bare)).toBeNull()
    expect(candidateParties({ ...bare, emisor: null, cliente: "Taller Norte, S.L." })).toBe("Para Taller Norte, S.L.")
    expect(candidateParties({ ...bare, emisor: null })).toBeNull()
  })

  test("un importe en otro formato se enseña tal como está guardado", () => {
    expect(candidateTotal({ ...full, total: "1.210,00 EUR" })).toBe("1.210,00 EUR")
  })

  test("el nombre accesible empieza por el número y lista cada campo", () => {
    expect(candidateName(full)).toBe(
      "Factura A-2026/014, emisor Suministros Aranda, S.L., cliente Taller Norte, S.L., fecha 12/02/2026, total 1.210,00 €"
    )
    expect(candidateName(bare)).toBe("Factura B-77, emisor Clara Ibáñez Roca")
  })

  test("cuenta las facturas que la lista deja fuera", () => {
    expect(hiddenCandidates(CLARIFICATION)).toBe(0)
    expect(hiddenCandidates({ ...CLARIFICATION, total: 7 })).toBe(5)
  })
})

test.describe("tarjeta de aclaración", () => {
  test("no es un rechazo: pregunta corta, sin «Sin evidencia» ni sugerencias de sección", async ({ page }) => {
    await askAmbiguous(page)
    await expect(card(page).getByRole("heading", { name: "¿De qué factura?" })).toBeVisible()
    await expect(page.getByTestId("refusal-notice")).toHaveCount(0)
    await expect(page.getByText("Sin evidencia suficiente")).toHaveCount(0)
    await expect(page.getByText(/No hay evidencia/)).toHaveCount(0)
    await expect(page.getByText("Apartados relacionados")).toHaveCount(0)
    await expect(page.getByText(/motivo:/)).toHaveCount(0)
  })

  test("cada candidata es un botón con número, emisor, fecha y total solo si existen", async ({ page }) => {
    await askAmbiguous(page)
    const buttons = card(page).getByTestId("clarification-candidate")
    await expect(buttons).toHaveCount(2)
    const first = buttons.nth(0)
    await expect(first).toContainText("A-2026/014")
    await expect(first).toContainText("12/02/2026")
    await expect(first).toContainText("De Suministros Aranda, S.L. para Taller Norte, S.L.")
    await expect(first).toContainText("1.210,00 €")
    const second = buttons.nth(1)
    await expect(second).toContainText("B-77")
    await expect(second).toContainText("De Clara Ibáñez Roca")
    await expect(second).not.toContainText("€")
    await expect(second).not.toContainText("/")
    await expect(card(page).getByRole("group", { name: "¿De qué factura?" })).toBeVisible()
    await expect(first).toHaveAccessibleName(/^Factura A-2026\/014, emisor Suministros Aranda/)
  })

  test("al pulsar una candidata se reenvía la pregunta desambiguada y llega su respuesta", async ({ page }) => {
    const { questions } = await askAmbiguous(page)
    await card(page).getByTestId("clarification-candidate").nth(0).click()
    await expect(page.getByTestId("assistant-message").nth(1)).toHaveAttribute("data-kind", "answer")
    expect(questions).toEqual([QUESTION, "¿Cuál es el importe total de la factura A-2026/014?"])
    await expect(page.getByTestId("answer-text")).toContainText("1.210,00 €")
  })

  test("se navega con el teclado: Tab llega, las flechas mueven y Intro elige", async ({ page }) => {
    const { questions } = await askAmbiguous(page)
    const buttons = card(page).getByTestId("clarification-candidate")
    await buttons.nth(0).focus()
    await expect(buttons.nth(0)).toBeFocused()
    await page.keyboard.press("ArrowDown")
    await expect(buttons.nth(1)).toBeFocused()
    await page.keyboard.press("ArrowDown")
    await expect(buttons.nth(1)).toBeFocused()
    await page.keyboard.press("ArrowUp")
    await expect(buttons.nth(0)).toBeFocused()
    await page.keyboard.press("End")
    await expect(buttons.nth(1)).toBeFocused()
    await page.keyboard.press("Enter")
    await expect(page.getByTestId("assistant-message").nth(1)).toHaveAttribute("data-kind", "answer")
    expect(questions.at(-1)).toBe("¿Cuál es el importe total de la factura B-77?")
  })

  test("si hay más facturas de las que caben lo dice y pide acotar", async ({ page }) => {
    await askAmbiguous(page, { ...CLARIFICATION, total: 7, detail: "Hay 7 facturas de Taller Norte, S.L." })
    await expect(card(page)).toContainText("Hay 7 facturas de Taller Norte, S.L.")
    await expect(card(page)).toContainText("Hay 5 facturas más. Indica el número o la fecha en la pregunta.")
  })

  test("copiar la aclaración da la pregunta y las candidatas", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await askAmbiguous(page)
    await page.getByTestId("copy-answer").click()
    const copied = await page.evaluate(() => navigator.clipboard.readText())
    expect(copied).toContain("¿De qué factura?")
    expect(copied).toContain("- Factura B-77, emisor Clara Ibáñez Roca")
  })
})
