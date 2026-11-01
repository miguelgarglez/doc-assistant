import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { mockBackend } from "./mocks"

test("revisa con redacciones, confirma y puede descartar desde teclado", async ({ page }) => {
  await mockBackend(page)
  let status = "nuevo"
  let payload: Record<string, unknown> | null = null
  const item = { feedback_id: "f1", request_id: "r1", conversation_id: "c1", created_at: "2026-11-01T10:00:00Z", kind: "incorrecta", comment: "Ana Sol y ana@example.com", status: "nuevo", expected_answer: null, trace: {} }
  await page.route("**/api/history/feedback**", async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith("/decision")) { payload = route.request().postDataJSON(); status = String(payload?.status); return route.fulfill({ json: { saved: true } }) }
    if (url.pathname.endsWith("/counts")) return route.fulfill({ json: { [status]: 1 } })
    if (url.pathname.endsWith("/original")) return route.fulfill({ json: { question: "¿Qué debe Ana Sol?", result: { answer: "100 €", citations: [{ doc: "Documento", quote: "100 €" }] } } })
    if (url.pathname.endsWith("/f1")) return route.fulfill({ json: { ...item, status } })
    return route.fulfill({ json: url.searchParams.get("status") === status ? [{ ...item, status }] : [] })
  })
  await page.goto("/revision")
  await expect(page.getByText("¿Qué debe Ana Sol?", { exact: true })).toBeVisible()
  await expect(page.getByText("Documento", { exact: true })).toBeVisible()
  await expect(page.locator("mark").filter({ hasText: "Ana Sol" }).first()).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
  await page.getByLabel("Respuesta esperada").fill("Importe disponible en el documento")
  await page.getByLabel("Comentario para exportar").fill("Falta un dato")
  await page.getByLabel("Contexto redactado para exportar (opcional)").fill("Importe omitido")
  await page.getByRole("checkbox", { name: "He comprobado que hay un fallo real." }).check()
  await page.getByRole("checkbox", { name: "He revisado toda la vista previa y quitado los datos sensibles." }).check()
  await page.getByText("Vista previa del registro JSONL").click()
  await expect(page.getByText("Importe omitido", { exact: false }).last()).toBeVisible()
  await page.getByRole("button", { name: "Marcar revisado" }).click()
  await expect.poll(() => status).toBe("revisado")
  expect(payload).toMatchObject({ redacted_comment: "Falta un dato", redacted_context: "Importe omitido", confirmed_no_sensitive_data: true })
  await page.getByRole("tab", { name: /Revisados/ }).click()
  await expect(page.getByRole("heading", { name: "Detalle del aviso" })).toBeVisible()
  await page.locator("body").click({ position: { x: 900, y: 20 } })
  await page.keyboard.press("d")
  await expect.poll(() => status).toBe("descartado")
})
