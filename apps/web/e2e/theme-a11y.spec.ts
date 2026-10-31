import path from "node:path"

import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

import { askAnswerWithCitation, DEMO_QUESTION, PAGE_PNG } from "./fixtures"

const SCREENSHOT_DIR = path.join("..", "..", "evidence", "screenshots")

async function stabilize(page: Page) {
  await page.evaluate(() => document.fonts.ready)
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
    `,
  })
}

async function setTheme(page: Page, theme: "industrial" | "neutral", dark = false) {
  await page.evaluate(
    ([nextTheme, nextDark]) => {
      localStorage.setItem("doc-assistant.theme", nextTheme)
      localStorage.setItem("doc-assistant.mode", nextDark ? "dark" : "light")
      document.documentElement.dataset.theme = nextTheme
      document.documentElement.classList.toggle("dark", nextDark)
    },
    [theme, dark] as const
  )
}

async function gotoThemed(
  page: Page,
  path: string,
  theme: "industrial" | "neutral",
  dark: boolean
) {
  await page.goto(path)
  await setTheme(page, theme, dark)
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme)
  if (dark) {
    await expect(page.locator("html")).toHaveClass(/dark/)
  } else {
    await expect(page.locator("html")).not.toHaveClass(/dark/)
  }
  await page.getByTestId(theme === "industrial" ? "theme-industrial" : "theme-neutral").click()
  if (dark !== (await page.locator("html").evaluate((el) => el.classList.contains("dark")))) {
    await page.getByTestId("mode-toggle").click()
  }
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme)
}

async function mockAsk(page: Page) {
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

test("swap de tema industrial ↔ neutral", async ({ page }) => {
  await page.goto("/")
  await expect(page.locator("html")).toHaveAttribute("data-theme", "industrial")
  await page.getByTestId("theme-neutral").click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "neutral")
  await page.getByTestId("theme-industrial").click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "industrial")
  await page.getByTestId("mode-toggle").click()
  await expect(page.locator("html")).toHaveClass(/dark/)
})

test.describe("axe a11y", () => {
  test.use({ reducedMotion: "reduce" })
  for (const theme of ["industrial", "neutral"] as const) {
    for (const dark of [false, true]) {
      const label = `${theme}-${dark ? "dark" : "light"}`

      test(`home sin violaciones serias (${label})`, async ({ page }) => {
        await mockAsk(page)
        await gotoThemed(page, "/", theme, dark)
        await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
        await page.getByRole("button", { name: "Consultar" }).click()
        await expect(page.getByTestId("answer-card")).toBeVisible()

        await page.mouse.move(0, 0)
        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa"])
          .analyze()
        const serious = results.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical"
        )
        expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
      })

      test(`/design sin violaciones serias (${label})`, async ({ page }) => {
        await gotoThemed(page, "/design", theme, dark)
        await expect(page.getByTestId("design-page")).toBeVisible()
        await page.mouse.move(0, 0)
        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa"])
          .analyze()
        const serious = results.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical"
        )
        expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
      })
    }
  }
})

test.describe("capturas tema y design", () => {
  for (const theme of ["industrial", "neutral"] as const) {
    for (const viewport of [
      { name: "desktop", size: { width: 1280, height: 800 } },
      { name: "mobile", size: { width: 390, height: 844 } },
    ] as const) {
      test(`home ${theme} ${viewport.name}`, async ({ page }) => {
        await mockAsk(page)
        await page.setViewportSize(viewport.size)
        await gotoThemed(page, "/", theme, false)
        await stabilize(page)
        await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
        await page.getByRole("button", { name: "Consultar" }).click()
        await expect(page.getByTestId("answer-card")).toBeVisible()
        const suffix = viewport.name === "mobile" ? "-mobile" : ""
        await page.screenshot({
          path: path.join(SCREENSHOT_DIR, `theme-${theme}${suffix}.png`),
          fullPage: true,
        })
      })

      test(`design ${theme} ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize(viewport.size)
        await gotoThemed(page, "/design", theme, false)
        await stabilize(page)
        const suffix = viewport.name === "mobile" ? "-mobile" : ""
        await page.screenshot({
          path: path.join(SCREENSHOT_DIR, `design-${theme}${suffix}.png`),
          fullPage: true,
        })
      })
    }
  }
})

test("CLS home bajo tras respuesta", async ({ page }) => {
  await mockAsk(page)
  await page.goto("/")
  await page.evaluate(() => {
    ;(window as unknown as { __cls: number }).__cls = 0
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const shift = entry as PerformanceEntry & { value: number; hadRecentInput: boolean }
        if (!shift.hadRecentInput) {
          ;(window as unknown as { __cls: number }).__cls += shift.value
        }
      }
    }).observe({ type: "layout-shift", buffered: true })
  })
  await page.getByLabel("Pregunta").fill(DEMO_QUESTION)
  await page.getByRole("button", { name: "Consultar" }).click()
  await expect(page.getByTestId("answer-card")).toBeVisible()
  await page.waitForTimeout(500)
  const cls = await page.evaluate(
    () => (window as unknown as { __cls: number }).__cls
  )
  expect(cls).toBeLessThan(0.1)
})
