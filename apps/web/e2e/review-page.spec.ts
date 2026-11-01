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
  await expect(page.getByText("No hay avisos en esta categoría.")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Detalle del aviso" })).toHaveCount(0)
  await page.getByRole("tab", { name: /Revisados/ }).click()
  await expect(page.getByRole("heading", { name: "Detalle del aviso" })).toBeVisible()
  await page.locator("body").click({ position: { x: 900, y: 20 } })
  await page.keyboard.press("d")
  await expect.poll(() => status).toBe("descartado")
})

test("permite reintentar el detalle y conserva el aviso si falla el guardado", async ({ page }) => {
  await mockBackend(page)
  let detailAttempts = 0
  const item = { feedback_id: "f2", request_id: "r2", conversation_id: "c2", created_at: "2026-11-01T10:00:00Z", kind: "incorrecta", comment: "Aviso de prueba", status: "nuevo", expected_answer: null, trace: {} }
  await page.route("**/api/history/feedback**", (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith("/counts")) return route.fulfill({ json: { nuevo: 1 } })
    if (url.pathname.endsWith("/decision")) return route.fulfill({ status: 503, json: {} })
    if (url.pathname.endsWith("/original")) return route.fulfill({ status: 404, json: {} })
    if (url.pathname.endsWith("/f2")) { detailAttempts++; return route.fulfill(detailAttempts === 1 ? { status: 503, json: {} } : { json: item }) }
    return route.fulfill({ json: [item] })
  })
  await page.goto("/revision")
  await expect(page.getByRole("alert").filter({ hasText: "No se pudo cargar el aviso" })).toBeVisible()
  await page.getByRole("button", { name: "Reintentar detalle" }).click()
  await expect(page.getByRole("heading", { name: "Detalle del aviso" })).toBeVisible()
  await page.getByRole("button", { name: "Descartar" }).click()
  await expect(page.getByText("No se pudo guardar; se ha restaurado el estado anterior.")).toBeVisible()
  await expect(page.getByRole("button", { name: /Aviso de prueba/ })).toBeVisible()
})

for (const theme of ["industrial", "neutral"]) {
  for (const mode of ["light", "dark"]) {
    test(`contraste de revisión, Sistema e historial: ${theme} ${mode}`, async ({ page }) => {
      await page.addInitScript(([selectedTheme, selectedMode]) => {
        localStorage.setItem("doc-assistant.theme", selectedTheme)
        localStorage.setItem("doc-assistant.mode", selectedMode)
      }, [theme, mode])
      await mockBackend(page)
      const item = { feedback_id: "f", request_id: "r", conversation_id: "c", created_at: "2026-11-01T10:00:00Z", kind: "incorrecta", comment: "Aviso", status: "nuevo", expected_answer: null, trace: {} }
      await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: true, enabled: true, initialization_error: null, retention_days: 30, pending: 0, failures: [] } }))
      await page.route("**/api/history/requests?**", (route) => route.fulfill({ json: [{ request_id: "r", conversation_id: "c", created_at: "2026-11-01T10:00:00Z", kind: "answer", status: "completed", elapsed_s: 1 }] }))
      await page.route("**/api/history/conversations?**", (route) => route.fulfill({ json: [{ conversation_id: "c", question: "Consulta", updated_at: "2026-11-01T10:00:00Z", count: 1 }] }))
      await page.route("**/api/history/feedback**", (route) => {
        const path = new URL(route.request().url()).pathname
        if (path.endsWith("counts")) return route.fulfill({ json: { nuevo: 1 } })
        if (path.endsWith("original")) return route.fulfill({ json: { question: "Consulta", result: { answer: "Respuesta", citations: [] } } })
        if (path.endsWith("/f")) return route.fulfill({ json: item })
        return route.fulfill({ json: [item] })
      })
      await page.goto("/revision")
      await expect(page.getByRole("heading", { name: "Detalle del aviso" })).toBeVisible()
      expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
      await page.goto("/sistema")
      await expect(page.getByRole("button", { name: "Copiar identificador r" })).toBeVisible()
      expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
      await page.getByRole("button", { name: "Historial" }).click()
      await expect(page.getByRole("dialog", { name: "Historial" }).getByText("Consulta", { exact: true })).toBeVisible()
      expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
    })
  }
}
