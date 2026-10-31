import { expect, test } from "@playwright/test"

import { ask, mockBackend, sse, step, type SseEvent } from "./mocks"
import { refusalCopy } from "../src/lib/chat/refusal-copy"

const GENERIC = "No dispongo de esa información en los documentos"
const refusal = (reason: string, answer = GENERIC) => ({ answer, reason, suggestions: [] })

function refusalStream(reason: string, answer: string): SseEvent[] {
  return [
    step("route", "running", "Analizando la pregunta"),
    step("route", "done", "Pregunta sobre el contenido de las fuentes", 0.01),
    ["refusal", { answer, reason, retract: true, suggestions: [] }],
    ["done", { ok: false, answer, citations: [], reason, suggestions: [], inline: "none", timings: { total: 0.4 } }],
  ]
}

test.describe("copy de la tarjeta de rechazo: función pura", () => {
  test("el rechazo genérico propone qué hacer en lugar de repetir la frase del servicio", () => {
    for (const reason of ["llm_unanswerable", "verify:numbers", "verify:quote_not_found", "no_evidence", "algo_nuevo"]) {
      const copy = refusalCopy(refusal(reason))
      expect(copy.title).toBe("No lo encuentro en tus fuentes")
      expect(copy.body).toBe("Prueba con otras palabras o añade el documento que la contiene.")
    }
  })

  test("un texto específico del servicio se conserva", () => {
    expect(refusalCopy(refusal("invoice:factura_no_encontrada", "No hay ninguna factura con número X-1."))).toEqual({
      title: "Sin coincidencias en las facturas",
      body: "No hay ninguna factura con número X-1.",
    })
    expect(refusalCopy(refusal("empty_index", "Todavía no hay documentos indexados. Sube PDFs en Fuentes y vuelve a preguntar."))).toEqual({
      title: "Aún no hay fuentes",
      body: "Todavía no hay documentos indexados. Sube PDFs en Fuentes y vuelve a preguntar.",
    })
  })

  test("las facturas distinguen entre no encontrar, faltar un dato y no entender la pregunta", () => {
    expect(refusalCopy(refusal("invoice:campo_ausente:iban", "Ese dato no consta en la factura.")).title).toBe("Falta un dato en las facturas")
    expect(refusalCopy(refusal("invoice:plan_invalido")).title).toBe("No he podido buscar eso en las facturas")
    expect(refusalCopy(refusal("invoice:plan_invalido")).body).toContain("número de factura")
  })

  test("ningún texto enseña un código interno", () => {
    const reasons = [
      "llm_unanswerable",
      "verify:numbers",
      "empty_index",
      "pregunta_vacia",
      "invoice:plan_invalido",
      "invoice:campo_ausente:iban",
      "invoice:sin_resultados",
    ]
    for (const reason of reasons) {
      const copy = refusalCopy(refusal(reason))
      expect(`${copy.title} ${copy.body}`).not.toMatch(/llm_|verify|invoice:|_|motivo/)
    }
  })
})

test.describe("tarjeta de rechazo", () => {
  test("no enseña «motivo:» ni el código; el código sale en Sistema", async ({ page }) => {
    await mockBackend(page, {
      ask: (route) => route.fulfill({ contentType: "text/event-stream", body: sse(refusalStream("llm_unanswerable", GENERIC)) }),
    })
    await page.goto("/")
    await ask(page, "¿Cuánto cuesta el robot?")
    const notice = page.getByTestId("refusal-notice")
    await expect(notice).toBeVisible()
    await expect(notice.getByRole("heading")).toHaveText("No lo encuentro en tus fuentes")
    await expect(notice).not.toContainText(/motivo|llm_unanswerable/)
    await expect(page.getByText(/No hay evidencia en las fuentes/)).toHaveCount(0)
    await page.getByTestId("copy-answer").click()
    await page.goto("/sistema")
    await expect(page.getByTestId("trace-code")).toHaveText("llm_unanswerable")
  })
})
