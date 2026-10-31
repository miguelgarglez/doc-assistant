import { expect, test } from "@playwright/test"

import { mockBackend } from "./mocks"

test("cambio de tema industrial ↔ neutral y modo oscuro, con persistencia", async ({ page }) => {
  await mockBackend(page)
  await page.goto("/ajustes")
  await expect(page.locator("html")).toHaveAttribute("data-theme", "industrial")
  await page.getByTestId("theme-neutral").click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "neutral")
  await page.getByTestId("mode-toggle").click()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.reload()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "neutral")
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.getByTestId("theme-industrial").click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", "industrial")
})
