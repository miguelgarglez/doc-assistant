"use client"

import { Loader2Icon, MaximizeIcon, MinusIcon, PlusIcon } from "lucide-react"
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  boundsOf,
  clampView,
  FIT,
  fitSize,
  focusView,
  panBy,
  zoomAt,
  zoomStep,
  type PageRect,
  type Point,
  type Size,
  type View,
} from "@/features/viewer/pan-zoom"
import { cn } from "@/lib/utils"

type PageCanvasProps = {
  src: string
  alt: string
  /** Highlighted areas, as page fractions. The view centers on them whenever they change. */
  rects: readonly PageRect[]
  /** Highlights are still being located; the page shows without them meanwhile. */
  locating?: boolean
}

type Gesture = { pointers: Map<number, Point>; pinch: number | null }

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y)
const middle = (a: Point, b: Point): Point => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })

/** Page image with zoom and pan (wheel, drag, pinch, double click, buttons and +/-/0 keys) and highlight rectangles. */
export function PageCanvas({ src, alt, rects, locating = false }: PageCanvasProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const gesture = useRef<Gesture>({ pointers: new Map(), pinch: null })
  const [natural, setNatural] = useState<Size | null>(null)
  const [failed, setFailed] = useState(false)
  const [viewport, setViewport] = useState<Size>({ w: 0, h: 0 })
  const [view, setView] = useState<View>(FIT)
  const [dragging, setDragging] = useState(false)

  const page = natural ? fitSize(natural, viewport) : { w: 0, h: 0 }
  const pageRef = useRef(page)
  const viewportSizeRef = useRef(viewport)
  useLayoutEffect(() => {
    pageRef.current = page
    viewportSizeRef.current = viewport
  })

  useLayoutEffect(() => {
    const element = viewportRef.current
    if (!element) return
    const measure = () => setViewport({ w: element.clientWidth, h: element.clientHeight })
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const focusKey = rects.map((rect) => `${rect.x},${rect.y},${rect.w},${rect.h}`).join("|")
  const ready = natural !== null && viewport.w > 0
  const resetKey = `${src}|${focusKey}`
  const [settledKey, setSettledKey] = useState<string | null>(null)
  if (ready && settledKey !== resetKey) {
    // New page or new highlight: bring the highlighted area into sight (or the whole page).
    setSettledKey(resetKey)
    const area = boundsOf(rects)
    setView(area ? focusView(area, page, viewport) : clampView(FIT, page, viewport))
  }
  const shown = ready ? clampView(view, page, viewport) : view

  const apply = useCallback((update: (current: View, page: Size, viewport: Size) => View) => {
    setView((current) => update(current, pageRef.current, viewportSizeRef.current))
  }, [])

  const anchorOf = useCallback((clientX: number, clientY: number): Point => {
    const box = viewportRef.current?.getBoundingClientRect()
    return { x: clientX - (box?.left ?? 0), y: clientY - (box?.top ?? 0) }
  }, [])

  useEffect(() => {
    const element = viewportRef.current
    if (!element) return
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      const factor = Math.exp(-event.deltaY * (event.ctrlKey ? 0.01 : 0.0018))
      const anchor = anchorOf(event.clientX, event.clientY)
      apply((current, size, box) => zoomAt(current, factor, anchor, size, box))
    }
    element.addEventListener("wheel", onWheel, { passive: false })
    return () => element.removeEventListener("wheel", onWheel)
  }, [anchorOf, apply])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return
      if (event.key === "+" || event.key === "=") apply((current, size, box) => zoomStep(current, 1, size, box))
      else if (event.key === "-" || event.key === "_") apply((current, size, box) => zoomStep(current, -1, size, box))
      else if (event.key === "0") apply((_, size, box) => clampView(FIT, size, box))
      else return
      event.preventDefault()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [apply])

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("[data-canvas-control]")) return
    event.currentTarget.setPointerCapture(event.pointerId)
    const state = gesture.current
    state.pointers.set(event.pointerId, anchorOf(event.clientX, event.clientY))
    state.pinch = state.pointers.size === 2 ? distance(...(Array.from(state.pointers.values()) as [Point, Point])) : null
    setDragging(true)
  }

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const state = gesture.current
    const previous = state.pointers.get(event.pointerId)
    if (!previous) return
    const next = anchorOf(event.clientX, event.clientY)
    state.pointers.set(event.pointerId, next)
    if (state.pointers.size === 2 && state.pinch) {
      const [a, b] = Array.from(state.pointers.values()) as [Point, Point]
      const span = distance(a, b)
      const factor = span / state.pinch
      state.pinch = span
      apply((current, size, box) => zoomAt(current, factor, middle(a, b), size, box))
    } else if (state.pointers.size === 1) {
      apply((current, size, box) => panBy(current, next.x - previous.x, next.y - previous.y, size, box))
    }
  }

  const onPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    const state = gesture.current
    state.pointers.delete(event.pointerId)
    state.pinch = null
    if (state.pointers.size === 0) setDragging(false)
  }

  const onDoubleClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("[data-canvas-control]")) return
    const anchor = anchorOf(event.clientX, event.clientY)
    apply((current, size, box) => (current.scale > 1.01 ? clampView(FIT, size, box) : zoomAt(current, 2.5, anchor, size, box)))
  }

  const zoomed = shown.scale > 1.01

  return (
    <div
      className={cn(
        "relative size-full touch-none overflow-hidden bg-muted/60 select-none",
        zoomed ? (dragging ? "cursor-grabbing" : "cursor-grab") : "cursor-zoom-in"
      )}
      data-testid="page-canvas"
      data-scale={shown.scale.toFixed(2)}
      onDoubleClick={onDoubleClick}
      onPointerCancel={onPointerEnd}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerEnd}
      ref={viewportRef}
    >
      <div
        className="absolute top-0 left-0 origin-top-left shadow-[var(--shadow-panel)]"
        style={{
          width: page.w,
          height: page.h,
          transform: `translate3d(${shown.x}px, ${shown.y}px, 0) scale(${shown.scale})`,
          visibility: ready ? "visible" : "hidden",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- PNG dinámico del proxy */}
        <img
          alt={alt}
          className="block size-full bg-white"
          draggable={false}
          onError={() => setFailed(true)}
          onLoad={(event) => {
            setFailed(false)
            setNatural({ w: event.currentTarget.naturalWidth, h: event.currentTarget.naturalHeight })
          }}
          src={src}
        />
        {rects.map((rect, index) => (
          <span
            aria-hidden
            className="pointer-events-none absolute animate-in rounded-[2px] fade-in-0 duration-200 motion-reduce:animate-none"
            data-testid="page-highlight"
            key={`${focusKey}-${index}`}
            style={{
              left: `${rect.x * 100}%`,
              top: `${rect.y * 100}%`,
              width: `${rect.w * 100}%`,
              height: `${rect.h * 100}%`,
              /* The page is always white paper, so the mark keeps one colour in both modes. */
              background: "oklch(0.88 0.17 95 / 0.62)",
              mixBlendMode: "multiply",
              outline: "1px solid oklch(0.7 0.16 80 / 0.7)",
            }}
          />
        ))}
      </div>

      {!natural && !failed ? (
        <div className="absolute inset-0 grid place-items-center text-muted-foreground" role="status">
          <span className="flex items-center gap-2 text-sm">
            <Loader2Icon aria-hidden className="size-4 animate-spin motion-reduce:animate-none" /> Cargando página…
          </span>
        </div>
      ) : null}
      {failed ? (
        <p className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-muted-foreground" role="alert">
          No se pudo cargar la imagen de la página.
        </p>
      ) : null}

      <div className="absolute right-3 bottom-3 flex items-center gap-1 rounded-lg border border-border bg-card/95 p-1 shadow-[var(--shadow-panel)]" data-canvas-control>
        {locating ? (
          <span className="flex items-center gap-1.5 px-1.5 text-xs text-muted-foreground" role="status">
            <Loader2Icon aria-hidden className="size-3 animate-spin motion-reduce:animate-none" /> Localizando
          </span>
        ) : null}
        <Button aria-label="Alejar" disabled={shown.scale <= 1.001} onClick={() => apply((current, size, box) => zoomStep(current, -1, size, box))} size="icon-sm" title="Alejar (−)" variant="ghost">
          <MinusIcon />
        </Button>
        <span className="min-w-10 text-center font-mono text-xs tabular-nums text-muted-foreground" data-testid="zoom-level">
          {Math.round(shown.scale * 100)}%
        </span>
        <Button aria-label="Acercar" onClick={() => apply((current, size, box) => zoomStep(current, 1, size, box))} size="icon-sm" title="Acercar (+)" variant="ghost">
          <PlusIcon />
        </Button>
        <Button aria-label="Ajustar a la ventana" disabled={!zoomed} onClick={() => apply((_, size, box) => clampView(FIT, size, box))} size="icon-sm" title="Ajustar (0)" variant="ghost">
          <MaximizeIcon />
        </Button>
      </div>
    </div>
  )
}
