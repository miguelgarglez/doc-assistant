import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

import { mockBackend } from "./mocks"

test("muestra fallos y exige revisión humana antes de exportar", async ({ page }) => {
  const browserErrors: string[] = []
  page.on("console", (message) => { if (message.type() === "error") browserErrors.push(message.text()) })
  await mockBackend(page)
  let reviewed = false
  let body: Record<string, unknown> | undefined
  await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: true, enabled: true, initialization_error: null, retention_days: 30, pending: 1, failures: [{ request_id: "request-failed", error: "OSError" }] } }))
  await page.route("**/api/history/feedback?**", (route) => route.fulfill({ json: reviewed ? [] : [{ feedback_id: "feedback-demo", request_id: "request-demo", conversation_id: "conversation-demo", created_at: "2026-10-31T10:00:00Z", comment: "La cifra es incorrecta", trace: { request_id: "request-demo", conversation_id: "conversation-demo" } }] }))
  await page.route("**/api/history/feedback/feedback-demo/review", async (route) => {
    body = route.request().postDataJSON() as Record<string, unknown>
    reviewed = true
    await route.fulfill({ json: { reviewed: true } })
  })
  await page.goto("/sistema")
  await expect(page.getByText("Guardados pendientes: 1")).toBeVisible()
  await expect(page.getByText("request-failed: OSError")).toBeVisible()
  await page.getByRole("button", { name: "Revisar" }).click()
  const dialog = page.getByRole("dialog", { name: "Revisar aviso" })
  await expect(dialog.getByText(/no incluye contexto/)).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
  await dialog.getByLabel("Respuesta esperada", { exact: true }).fill("La cifra correcta es otra")
  const submit = dialog.getByRole("button", { name: "Marcar revisado" })
  await expect(submit).toBeDisabled()
  await dialog.getByRole("checkbox", { name: /fallo real/ }).check()
  await dialog.getByRole("checkbox", { name: /datos sensibles/ }).check()
  await submit.click()
  await expect(page.getByText("Aviso revisado")).toBeVisible()
  await expect(page.getByText("No hay avisos pendientes.")).toBeVisible()
  expect(body).toMatchObject({ conversation_id: "conversation-demo", expected_answer: "La cifra correcta es otra", confirmed_error: true, confirmed_no_sensitive_data: true })
  await expect(page.getByRole("link", { name: "Exportar revisados" })).toHaveAttribute("href", "/api/history/feedback/export")
  expect(browserErrors.filter((message) => message.includes("nativeButton"))).toEqual([])
})

test("distingue un fallo de apertura de la desactivación administrativa", async ({ page }) => {
  await mockBackend(page)
  await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: false, enabled: true, initialization_error: "OSError", retention_days: 30, pending: 1, failures: [{ request_id: "retry-request", error: "OSError" }] } }))
  await page.goto("/sistema")
  await expect(page.getByText("No disponible, reintentando")).toBeVisible()
  await expect(page.getByText("Error al abrir el almacén: OSError")).toBeVisible()
  await expect(page.getByText("retry-request: OSError")).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
})

test("permite revisar avisos más allá de la primera página", async ({ page }) => {
  await mockBackend(page)
  await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: true, enabled: true, initialization_error: null, retention_days: 30, pending: 0, failures: [] } }))
  const rows = Array.from({ length: 101 }, (_, index) => ({ feedback_id: `f-${index}`, request_id: `r-${index}`, conversation_id: `c-${index}`, created_at: "2026-10-31T10:00:00Z", comment: `Aviso ${index}`, trace: {} }))
  await page.route("**/api/history/feedback?**", (route) => {
    const query = new URL(route.request().url()).searchParams
    const offset = Number(query.get("offset") || 0)
    const limit = Number(query.get("limit"))
    return route.fulfill({ json: rows.slice(offset, offset + limit) })
  })
  await page.goto("/sistema")
  await expect(page.getByText("Aviso 99", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Cargar más avisos" }).click()
  await expect(page.getByText("Aviso 100", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Cargar más avisos" })).toHaveCount(0)
  await page.getByRole("listitem").filter({ hasText: "Aviso 100" }).getByRole("button", { name: "Revisar" }).click()
  await expect(page.getByRole("dialog", { name: "Revisar aviso" }).getByText("Aviso 100")).toBeVisible()
})
