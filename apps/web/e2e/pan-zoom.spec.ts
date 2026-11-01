import { expect, test } from "@playwright/test"

import { boundsOf, clampView, fitSize, focusView, panBy, zoomAt, zoomStep, MAX_SCALE } from "../src/features/viewer/pan-zoom"

const viewport = { w: 800, h: 600 }
const page = fitSize({ w: 612, h: 792 }, viewport)

test.describe("pan-zoom", () => {
  test("fits the page by height and keeps the aspect ratio", () => {
    expect(page.h).toBeCloseTo(600)
    expect(page.w / page.h).toBeCloseTo(612 / 792)
  })

  test("centers the page while it is smaller than the viewport", () => {
    const view = clampView({ scale: 1, x: 120, y: -40 }, page, viewport)
    expect(view.x).toBeCloseTo((viewport.w - page.w) / 2)
    expect(view.y).toBeCloseTo(0)
  })

  test("never leaves gaps once the page is larger than the viewport", () => {
    const view = clampView({ scale: 3, x: 500, y: 500 }, page, viewport)
    expect(view.x).toBeLessThanOrEqual(0)
    expect(view.y).toBeLessThanOrEqual(0)
    const far = clampView({ scale: 3, x: -99999, y: -99999 }, page, viewport)
    expect(far.x).toBeCloseTo(viewport.w - page.w * 3)
    expect(far.y).toBeCloseTo(viewport.h - page.h * 3)
  })

  test("zoom stays within bounds and keeps the anchored point", () => {
    let view = clampView({ scale: 1, x: 0, y: 0 }, page, viewport)
    const anchor = { x: 400, y: 300 }
    const pageX = (anchor.x - view.x) / view.scale
    view = zoomAt(view, 2, anchor, page, viewport)
    expect(view.scale).toBe(2)
    expect((anchor.x - view.x) / view.scale).toBeCloseTo(pageX)
    for (let step = 0; step < 30; step += 1) view = zoomStep(view, 1, page, viewport)
    expect(view.scale).toBe(MAX_SCALE)
    for (let step = 0; step < 60; step += 1) view = zoomStep(view, -1, page, viewport)
    expect(view.scale).toBe(1)
  })

  test("panning is clamped", () => {
    const zoomed = zoomAt({ scale: 1, x: 0, y: 0 }, 2, { x: 400, y: 300 }, page, viewport)
    const moved = panBy(zoomed, 10_000, 10_000, page, viewport)
    expect(moved.x).toBe(0)
    expect(moved.y).toBe(0)
  })

  test("focus centers the highlighted area", () => {
    const area = boundsOf([
      { x: 0.4, y: 0.5, w: 0.2, h: 0.02 },
      { x: 0.4, y: 0.52, w: 0.15, h: 0.02 },
    ])
    expect(area).not.toBeNull()
    const view = focusView(area!, page, viewport)
    expect(view.scale).toBeGreaterThan(1)
    const centerX = view.x + (area!.x + area!.w / 2) * page.w * view.scale
    const centerY = view.y + (area!.y + area!.h / 2) * page.h * view.scale
    expect(centerX).toBeCloseTo(viewport.w / 2, 0)
    expect(centerY).toBeCloseTo(viewport.h / 2, 0)
  })

  test("an area at the page edge is brought as close to the center as the page allows", () => {
    const narrow = { w: 500, h: 600 }
    const fitted = fitSize({ w: 612, h: 792 }, narrow)
    const view = focusView({ x: 0, y: 0, w: 0.3, h: 0.02 }, fitted, narrow)
    expect(view.scale).toBeGreaterThan(1)
    expect(view.x).toBeCloseTo(0)
    expect(view.y).toBeCloseTo(0)
  })

  test("an area as large as the page does not zoom in", () => {
    const view = focusView({ x: 0, y: 0, w: 1, h: 1 }, page, viewport)
    expect(view.scale).toBe(1)
  })

  test("no rectangles, no area", () => {
    expect(boundsOf([])).toBeNull()
  })
})
