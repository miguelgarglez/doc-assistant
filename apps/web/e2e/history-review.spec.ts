import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { mockBackend } from "./mocks"

test("muestra fallos y enlaza a la revisión humana", async ({ page }) => {
  await mockBackend(page)
  const item = { feedback_id: "feedback-demo", request_id: "request-demo", conversation_id: "conversation-demo", created_at: "2026-10-31T10:00:00Z", kind: "incorrecta", status: "nuevo", expected_answer: null, comment: "La cifra es incorrecta", trace: {} }
  await page.route("**/api/history/status", (route) => route.fulfill({ json: { active: true, enabled: true, initialization_error: null, retention_days: 30, pending: 1, failures: [{ request_id: "request-failed", error: "OSError" }] } }))
  await page.route("**/api/history/requests?**", (route) => route.fulfill({ json: [] }))
  await page.route("**/api/history/feedback**", (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith("/counts")) return route.fulfill({ json: { nuevo: 1 } })
    if (url.pathname.endsWith("/original")) return route.fulfill({ status: 404, json: {} })
    if (url.pathname.endsWith("/feedback-demo")) return route.fulfill({ json: item })
    return route.fulfill({ json: [item] })
  })
  await page.goto("/sistema")
  await expect(page.getByText("Guardados pendientes: 1")).toBeVisible()
  await expect(page.getByText("request-failed: OSError")).toBeVisible()
  await page.getByRole("link", { name: "Revisar", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Revisión de avisos" })).toBeVisible()
  await expect(page.getByText("La conversación original ya no está disponible.", { exact: false })).toBeVisible()
  await expect(page.getByRole("button", { name: "Marcar revisado" })).toBeDisabled()
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
  await expect(page.getByRole("link", { name: "Exportar revisados" })).toHaveAttribute("href", "/api/history/feedback/export")
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
  const rows = Array.from({ length: 101 }, (_, index) => ({ feedback_id: `f-${index}`, request_id: `r-${index}`, conversation_id: `c-${index}`, created_at: "2026-10-31T10:00:00Z", kind: "incorrecta", status: "nuevo", expected_answer: null, comment: `Aviso ${index}`, trace: {} }))
  await page.route("**/api/history/feedback**", (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith("/counts")) return route.fulfill({ json: { nuevo: 101 } })
    if (url.pathname.endsWith("/original")) return route.fulfill({ status: 404, json: {} })
    if (url.pathname.endsWith("/feedback")) {
      const offset = Number(url.searchParams.get("offset") || 0)
      return route.fulfill({ json: rows.slice(offset, offset + Number(url.searchParams.get("limit"))) })
    }
    return route.fulfill({ json: rows.find((item) => url.pathname.endsWith(`/${item.feedback_id}`)) })
  })
  await page.goto("/revision")
  await expect(page.getByRole("button", { name: /Aviso 49/ })).toBeVisible()
  await page.getByRole("button", { name: "Cargar más" }).click()
  await expect(page.getByRole("button", { name: /Aviso 99/ })).toBeVisible()
  await page.getByRole("button", { name: "Cargar más" }).click()
  await page.getByRole("button", { name: /Aviso 100/ }).click()
  await expect(page.getByText("Petición: r-100", { exact: false })).toBeVisible()
  await expect(page.getByRole("button", { name: "Cargar más" })).toHaveCount(0)
})
