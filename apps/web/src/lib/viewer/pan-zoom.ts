export type Size = { w: number; h: number }
export type Point = { x: number; y: number }
/** Page rectangle as fractions of the page, origin at the top left (same as the API). */
export type PageRect = { x: number; y: number; w: number; h: number }

/**
 * Pan and zoom of a page. `scale` is relative to the page fitted in the viewport (1 = whole page visible),
 * `x`/`y` are the translation in pixels of the fitted page.
 */
export type View = { scale: number; x: number; y: number }

export const MIN_SCALE = 1
export const MAX_SCALE = 6
export const ZOOM_STEP = 1.25
export const FOCUS_SCALE = 1.7

export const FIT: View = { scale: MIN_SCALE, x: 0, y: 0 }

/** Size of the page when it just fits the viewport, keeping its aspect ratio. */
export function fitSize(natural: Size, viewport: Size): Size {
  if (natural.w <= 0 || natural.h <= 0 || viewport.w <= 0 || viewport.h <= 0) return { w: 0, h: 0 }
  const ratio = Math.min(viewport.w / natural.w, viewport.h / natural.h)
  return { w: natural.w * ratio, h: natural.h * ratio }
}

function clampAxis(offset: number, content: number, viewport: number): number {
  if (content <= viewport) return (viewport - content) / 2
  return Math.min(0, Math.max(viewport - content, offset))
}

/** Keeps the page inside the viewport: centered while it is smaller, never leaving gaps once larger. */
export function clampView(view: View, page: Size, viewport: Size): View {
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.scale))
  return {
    scale,
    x: clampAxis(view.x, page.w * scale, viewport.w),
    y: clampAxis(view.y, page.h * scale, viewport.h),
  }
}

/** Zooms by `factor` keeping the page point under `anchor` (viewport pixels) where it is. */
export function zoomAt(view: View, factor: number, anchor: Point, page: Size, viewport: Size): View {
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.scale * factor))
  const ratio = scale / view.scale
  return clampView(
    { scale, x: anchor.x - (anchor.x - view.x) * ratio, y: anchor.y - (anchor.y - view.y) * ratio },
    page,
    viewport
  )
}

export function zoomStep(view: View, direction: 1 | -1, page: Size, viewport: Size): View {
  const center = { x: viewport.w / 2, y: viewport.h / 2 }
  return zoomAt(view, direction > 0 ? ZOOM_STEP : 1 / ZOOM_STEP, center, page, viewport)
}

export function panBy(view: View, dx: number, dy: number, page: Size, viewport: Size): View {
  return clampView({ ...view, x: view.x + dx, y: view.y + dy }, page, viewport)
}

/** Union of the rectangles, the area the viewer should bring into sight. */
export function boundsOf(rects: readonly PageRect[]): PageRect | null {
  if (rects.length === 0) return null
  const left = Math.min(...rects.map((rect) => rect.x))
  const top = Math.min(...rects.map((rect) => rect.y))
  const right = Math.max(...rects.map((rect) => rect.x + rect.w))
  const bottom = Math.max(...rects.map((rect) => rect.y + rect.h))
  return { x: left, y: top, w: right - left, h: bottom - top }
}

/** Zoom that shows the whole area with some air around, never beyond FOCUS_SCALE for small areas. */
export function focusView(area: PageRect, page: Size, viewport: Size): View {
  const width = Math.max(area.w * page.w, 1)
  const height = Math.max(area.h * page.h, 1)
  const fits = Math.min(viewport.w / (width * 1.6), viewport.h / (height * 1.6))
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, Math.min(FOCUS_SCALE, fits)))
  const centerX = (area.x + area.w / 2) * page.w * scale
  const centerY = (area.y + area.h / 2) * page.h * scale
  return clampView({ scale, x: viewport.w / 2 - centerX, y: viewport.h / 2 - centerY }, page, viewport)
}
