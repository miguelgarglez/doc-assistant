import path from "node:path"
import { readFileSync } from "node:fs"

import { expect, test, type Page } from "@playwright/test"

import {
  DEMO_QUESTION,
  askAnswerWithCitation,
  askRefusal,
  PAGE_PNG,
} from "./fixtures"

const FIXTURE_PDF = path.join(
  "..",
  "..",
  "evidence",
  "fixtures",
  "docs",
  "robot-demo.pdf"
)

async function mockAskOk(page: Page) {
  await page.route("**/api/ask", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(askAnswerWithCitation),
    })
  })
  await page.route("**/api/sources/**/pages/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: PAGE_PNG,
    })
  })
}

test.describe("chat UX", () => {
  test.use({
    permissions: ["clipboard-read", "clipboard-write"],
  })

  test("atajos: Enter envía, Cmd+K enfoca, ? abre ayuda", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await mockAskOk(page)
    await page.goto("/")

    const input = page.getByTestId("question-input")
    await input.click()
    await page.keyboard.press("Escape")
    await page.keyboard.press("Meta+k")
    await expect(input).toBeFocused()

    await input.fill(DEMO_QUESTION)
    await input.press("Enter")
    await expect(page.getByTestId("answer-card")).toBeVisible()

    await page.keyboard.press("Meta+/")
    await expect(page.getByTestId("shortcuts-help")).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByTestId("shortcuts-help")).toHaveCount(0)

    await page.getByTestId("open-shortcuts").click()
    await expect(page.getByTestId("shortcuts-help")).toBeVisible()
  })

  test("copiar respuesta y markdown con citas", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await mockAskOk(page)
    await page.goto("/")
    await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
    await page.getByRole("button", { name: "Consultar" }).click()
    await expect(page.getByTestId("answer-card")).toBeVisible()

    await page.getByTestId("copy-answer").click()
    await expect(
      page.getByTestId("toast").filter({ hasText: "copiada" })
    ).toBeVisible()
    const answerText = await page.evaluate(() => navigator.clipboard.readText())
    expect(answerText).toContain(askAnswerWithCitation.answer)

    await page.getByTestId("copy-markdown").click()
    await expect(
      page.getByTestId("toast").filter({ hasText: "Markdown" })
    ).toBeVisible()
    const md = await page.evaluate(() => navigator.clipboard.readText())
    expect(md).toContain("## Citas")
    expect(md).toContain(askAnswerWithCitation.citations[0].quote)
  })

  test("cancelar consulta en curso", async ({ page }) => {
    await page.route("**/api/ask", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 30_000))
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(askAnswerWithCitation),
      })
    })
    await page.goto("/")
    await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
    await page.getByRole("button", { name: "Consultar" }).click()
    await expect(page.getByTestId("ask-loading")).toBeVisible()
    await expect(page.getByTestId("cancel-ask")).toBeVisible()
    await page.getByTestId("cancel-ask").click({ force: true })
    await expect(page.getByTestId("ask-cancelled")).toBeVisible()
    await expect(page.getByText("Consulta cancelada.")).toBeVisible()
    await expect(page.getByRole("button", { name: "Consultar" })).toBeEnabled()
  })

  test("rechazo con diseño propio (no alert destructivo)", async ({ page }) => {
    await page.route("**/api/ask", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(askRefusal),
      })
    })
    await page.goto("/")
    await page.getByLabel("Pregunta").fill("pregunta sin evidencia")
    await page.getByRole("button", { name: "Consultar" }).click()
    const refusal = page.getByTestId("refusal-notice")
    await expect(refusal).toBeVisible()
    await expect(refusal).not.toHaveAttribute("data-variant", "destructive")
    await expect(page.getByTestId("ask-error-notice")).toHaveCount(0)
  })

  test("pegar PDF dispara subida a /documents", async ({ page }) => {
    let uploaded = false
    await page.route("**/api/documents", async (route) => {
      if (route.request().method() === "POST") {
        uploaded = true
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            doc_id: "demo-doc",
            n_chunks: 3,
            created: true,
          }),
        })
        return
      }
      await route.fallback()
    })
    await page.goto("/")
    const pdf = readFileSync(FIXTURE_PDF)
    const input = page.getByTestId("question-input")
    await input.focus()
    await page.evaluate(async (bytes) => {
      const file = new File([new Uint8Array(bytes)], "robot-demo.pdf", {
        type: "application/pdf",
      })
      const dt = new DataTransfer()
      dt.items.add(file)
      const target = document.querySelector(
        '[data-testid="question-input"]'
      ) as HTMLTextAreaElement
      target.dispatchEvent(
        new ClipboardEvent("paste", {
          clipboardData: dt,
          bubbles: true,
          cancelable: true,
        })
      )
    }, Array.from(pdf))
    await expect.poll(() => uploaded).toBe(true)
    await expect(page.getByTestId("document-upload-result")).toBeVisible()
  })

  test("historial ↑ en input vacío", async ({ page }) => {
    await mockAskOk(page)
    await page.goto("/")
    const input = page.getByTestId("question-input")
    await input.fill("primera pregunta de historial")
    await input.press("Enter")
    await expect(page.getByTestId("answer-card")).toBeVisible()
    await input.fill("")
    await input.press("ArrowUp")
    await expect(input).toHaveValue("primera pregunta de historial")
  })
})
