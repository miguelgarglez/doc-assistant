import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { ask, mockBackend, sse, answerEvents } from "./mocks"

test("abre una conversación, la continúa y confirma el borrado", async ({ page }) => {
  await mockBackend(page)
  let deleted = false
  let submittedConversation = ""
  const row = { conversation_id: "conversation-demo", question: "Pregunta guardada", updated_at: "2026-10-31T10:00:00Z", count: 1 }
  await page.route("**/api/history/conversations**", async (route) => {
    if (route.request().method() === "DELETE") {
      deleted = true
      await route.fulfill({ json: { deleted: 1 } })
    } else if (new URL(route.request().url()).pathname.endsWith("conversation-demo")) {
      await route.fulfill({ json: { items: [{ request_id: "old-request", question: "Pregunta guardada", result: { ok: true, answer: "Respuesta guardada", citations: [], reason: "", segments: [], blocks: [], follow_ups: [], blocks_version: 1 } }], next_cursor: null } })
    } else {
      await route.fulfill({ json: deleted ? [] : [row] })
    }
  })
  await page.route("**/api/ask/stream", async (route) => {
    submittedConversation = route.request().postDataJSON().conversation_id
    await route.fulfill({ contentType: "text/event-stream", body: sse(answerEvents()) })
  })
  await page.goto("/")
  await page.keyboard.press("Alt+h")
  const sheet = page.getByRole("dialog", { name: "Historial" })
  await expect(sheet.getByText("Pregunta guardada")).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([])
  await sheet.getByText("Pregunta guardada").click()
  await expect(page.getByText("Respuesta guardada")).toBeVisible()
  await ask(page, "Otra pregunta")
  await expect.poll(() => submittedConversation).toBe("conversation-demo")
  await page.keyboard.press("Alt+h")
  await sheet.getByRole("button", { name: "Borrar todo" }).click()
  const confirm = page.getByRole("dialog", { name: "¿Borrar todo el historial?" })
  await expect(confirm).toBeVisible()
  await confirm.getByRole("button", { name: "Borrar todo" }).click()
  await expect(sheet.getByText("No hay conversaciones guardadas.")).toBeVisible()
  expect(deleted).toBe(true)
})

test("busca y borra una conversación", async ({ page }) => {
  await mockBackend(page)
  let removed = false
  await page.route("**/api/history/conversations**", async (route) => {
    if (route.request().method() === "DELETE") {
      removed = true
      await route.fulfill({ json: { deleted: 1 } })
      return
    }
    const search = new URL(route.request().url()).searchParams.get("search")
    const rows = [{ conversation_id: "one", question: "Pregunta azul", updated_at: "2026-10-31T10:00:00Z", count: 1 }]
    await route.fulfill({ json: !removed && (!search || "Pregunta azul".toLowerCase().includes(search.toLowerCase())) ? rows : [] })
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Historial" }).click()
  const sheet = page.getByRole("dialog", { name: "Historial" })
  await expect(sheet.getByText("Pregunta azul")).toBeVisible()
  await sheet.getByLabel("Buscar en el historial").fill("rojo")
  await expect(sheet.getByText("No hay conversaciones guardadas.")).toBeVisible()
  await sheet.getByLabel("Buscar en el historial").fill("azul")
  await sheet.getByRole("button", { name: "Borrar Pregunta azul" }).click()
  await expect(sheet.getByText("No hay conversaciones guardadas.")).toBeVisible()
  expect(removed).toBe(true)
})
