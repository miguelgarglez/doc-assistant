"use client"

import { ChevronLeftIcon, ChevronRightIcon, XIcon } from "lucide-react"
import { useEffect, useState } from "react"

import { PageCanvas } from "@/features/viewer"
import { useHighlight, type HighlightState } from "@/features/viewer"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog"
import { Kbd } from "@/components/ui/kbd"
import { citationPage, isInvoiceCitation, sourcePageUrl } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"
import { citationLabel } from "@/features/chat/lib/citation-label"
import { HighlightedFragment } from "@/features/chat/highlight-fragment"
import { isEditableTarget } from "@/lib/shortcuts"
import { cn } from "@/lib/utils"

/** Chunks are stored with a "[doc · title · section]" header the viewer already shows elsewhere. */
function fragmentBody(fragment: string): string {
  return fragment.replace(/^\[[^\]]*\]\s*/, "")
}

type SourceViewerProps = {
  citations: Citation[]
  index: number
  onIndexChange: (index: number) => void
  onClose: () => void
}

/** Says, in the viewer itself, whether the cited fragment is marked on the page and why not when it is not. */
function highlightNotice(citation: Citation, state: HighlightState): { tone: "ok" | "muted"; text: string } | null {
  if (isInvoiceCitation(citation)) {
    return {
      tone: "muted",
      text: "El dato sale de una imagen leída con OCR, que no guarda posiciones. Se muestra la factura entera y, aquí al lado, el campo extraído.",
    }
  }
  if (state.status === "loading") return { tone: "muted", text: "Localizando el fragmento en la página…" }
  if (state.status === "error") return { tone: "muted", text: "No se pudo comprobar dónde está el fragmento. La página se muestra sin marcar." }
  if (state.status !== "ready") return null
  const { highlight } = state
  if (highlight.found) return { tone: "ok", text: "Fragmento resaltado en la página." }
  if (highlight.reason === "no_file") return { tone: "muted", text: "El PDF original ya no está en el servidor: se muestra la página sin marcar." }
  return {
    tone: "muted",
    text: "No se encontró el fragmento en la capa de texto de la página (puede ser una imagen o estar partido en columnas). Se muestra la página sin marcar.",
  }
}

/** Full-screen viewer of a cited page: highlighted fragment, zoom and pan, and navigation between citations and pages. */
export function SourceViewer({ citations, index, onIndexChange, onClose }: SourceViewerProps) {
  const safeIndex = Math.min(Math.max(index, 0), citations.length - 1)
  const citation = citations[safeIndex]
  const [pageByCitation, setPageByCitation] = useState<Record<string, number>>({})
  const citationKey = citation ? `${citation.chunk_id}:${safeIndex}` : ""
  const pageIndex = citation ? Math.min(pageByCitation[citationKey] ?? 0, Math.max(citation.pages.length - 1, 0)) : 0
  const page = citation ? citationPage(citation, pageIndex) : undefined
  const invoice = citation ? isInvoiceCitation(citation) : false
  const highlight = useHighlight(citation?.doc_id ?? "", page, citation?.quote ?? "", !invoice)

  const pageCount = citation?.pages.length ?? 0
  const setPageIndex = (next: number) => setPageByCitation((current) => ({ ...current, [citationKey]: next }))

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target)) return
      if (event.key === "ArrowLeft" && safeIndex > 0) onIndexChange(safeIndex - 1)
      else if (event.key === "ArrowRight" && safeIndex < citations.length - 1) onIndexChange(safeIndex + 1)
      else if ((event.key === "ArrowUp" || event.key === "PageUp") && pageIndex > 0) setPageByCitation((current) => ({ ...current, [citationKey]: pageIndex - 1 }))
      else if ((event.key === "ArrowDown" || event.key === "PageDown") && pageIndex < pageCount - 1) setPageByCitation((current) => ({ ...current, [citationKey]: pageIndex + 1 }))
      else if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "PageUp", "PageDown"].includes(event.key)) return
      event.preventDefault()
    }
    // Capture phase: the dialog's own focus handling stops arrow keys before they bubble to the window.
    window.addEventListener("keydown", onKeyDown, true)
    return () => window.removeEventListener("keydown", onKeyDown, true)
  }, [citationKey, citations.length, onIndexChange, pageCount, pageIndex, safeIndex])

  if (!citation) return null

  const notice = highlightNotice(citation, highlight)
  const rects = highlight.status === "ready" && highlight.highlight.found ? (highlight.highlight.rects ?? []) : []

  return (
    <Dialog onOpenChange={(open) => !open && onClose()} open>
      <DialogContent
        className="top-0 left-0 h-dvh w-screen max-w-none translate-x-0 translate-y-0 grid-rows-[auto_minmax(0,1fr)] gap-0 overflow-hidden rounded-none p-0 ring-0 data-open:zoom-in-100 data-closed:zoom-out-100 sm:max-w-none"
        data-testid="source-viewer"
        showCloseButton={false}
      >
        <header className="flex items-center gap-2 border-b border-border px-3 py-2 sm:px-4">
          <div className="min-w-0 flex-1">
            <DialogTitle className="truncate font-heading text-sm font-semibold">{citation.doc}</DialogTitle>
            <DialogDescription className="truncate font-mono text-xs text-muted-foreground">
              {citation.section ? `Sección ${citation.section}` : "Fragmento"}
              {page === undefined || invoice ? "" : `, página ${page}`}
            </DialogDescription>
          </div>
          {citations.length > 1 ? (
            <div aria-label="Navegación entre citas" className="flex shrink-0 items-center gap-0.5" role="group">
              <Button aria-label="Cita anterior" disabled={safeIndex <= 0} onClick={() => onIndexChange(safeIndex - 1)} size="icon-sm" variant="ghost">
                <ChevronLeftIcon />
              </Button>
              <span aria-live="polite" className="min-w-11 text-center font-mono text-xs tabular-nums text-muted-foreground" data-testid="viewer-position">
                {safeIndex + 1}/{citations.length}
              </span>
              <Button aria-label="Cita siguiente" disabled={safeIndex >= citations.length - 1} onClick={() => onIndexChange(safeIndex + 1)} size="icon-sm" variant="ghost">
                <ChevronRightIcon />
              </Button>
            </div>
          ) : null}
          <Button aria-label="Cerrar visor" onClick={onClose} size="icon-sm" variant="ghost">
            <XIcon />
          </Button>
        </header>

        <div className="flex min-h-0 flex-col md:flex-row">
          <div className="min-h-0 min-w-0 flex-1" data-testid="viewer-page">
            {page === undefined ? (
              <p className="grid size-full place-items-center p-6 text-center text-sm text-muted-foreground">Esta fuente no tiene página asociada.</p>
            ) : (
              <PageCanvas
                alt={`Página ${page} de ${citation.doc}`}
                key={`${citation.doc_id}:${page}`}
                locating={highlight.status === "loading"}
                rects={rects}
                src={sourcePageUrl(citation.doc_id, page)}
              />
            )}
          </div>

          <aside
            aria-label="Detalle de la cita"
            className="flex max-h-[38dvh] shrink-0 flex-col gap-4 overflow-y-auto border-t border-border bg-card p-4 md:max-h-none md:w-[22rem] md:border-t-0 md:border-l"
          >
            <section className="flex flex-col gap-1.5">
              <h3 className="text-xs font-medium text-muted-foreground">{invoice ? "Campo extraído" : "Fragmento citado"}</h3>
              <p className="text-sm leading-relaxed" data-testid="viewer-fragment">
                <HighlightedFragment fragment={fragmentBody(citation.fragment)} quote={citation.quote} />
              </p>
            </section>

            {notice ? (
              <p
                className={cn(
                  "flex items-start gap-2 rounded-md border px-2.5 py-2 text-xs leading-relaxed",
                  notice.tone === "ok" ? "border-border bg-muted/50 text-foreground" : "border-dashed border-border text-muted-foreground"
                )}
                data-testid="viewer-notice"
                role="status"
              >
                {notice.tone === "ok" ? <span aria-hidden className="mt-0.5 size-3 shrink-0 rounded-[3px]" style={{ background: "oklch(0.88 0.17 95)", outline: "1px solid oklch(0.7 0.16 80)" }} /> : null}
                <span>{notice.text}</span>
              </p>
            ) : null}

            {pageCount > 1 ? (
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">Páginas del fragmento</p>
                <div aria-label="Páginas del fragmento" className="flex items-center gap-0.5" role="group">
                  <Button aria-label="Página anterior del fragmento" disabled={pageIndex <= 0} onClick={() => setPageIndex(pageIndex - 1)} size="icon-xs" variant="ghost">
                    <ChevronLeftIcon />
                  </Button>
                  <span className="min-w-9 text-center font-mono text-xs tabular-nums text-muted-foreground">
                    p. {page} ({pageIndex + 1}/{pageCount})
                  </span>
                  <Button aria-label="Página siguiente del fragmento" disabled={pageIndex >= pageCount - 1} onClick={() => setPageIndex(pageIndex + 1)} size="icon-xs" variant="ghost">
                    <ChevronRightIcon />
                  </Button>
                </div>
              </div>
            ) : null}

            {citations.length > 1 ? (
              <nav aria-label="Citas de la respuesta" className="hidden flex-col gap-1 md:flex">
                <p className="text-xs font-medium text-muted-foreground">Citas de la respuesta</p>
                <ol className="flex flex-col gap-0.5">
                  {citations.map((item, position) => (
                    <li key={`${item.chunk_id}-${position}`}>
                      <button
                        aria-current={position === safeIndex ? "true" : undefined}
                        className={cn(
                          "flex w-full items-baseline gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors duration-150 ease-out outline-none focus-visible:ring-3 focus-visible:ring-ring/50 active:scale-[0.99] motion-reduce:transition-none",
                          position === safeIndex ? "bg-accent text-accent-foreground" : "text-muted-foreground [@media(hover:hover)]:hover:bg-muted"
                        )}
                        onClick={() => onIndexChange(position)}
                        type="button"
                      >
                        <span className="font-mono tabular-nums">{position + 1}</span>
                        <span className="min-w-0 truncate">{citationLabel(item)}</span>
                      </button>
                    </li>
                  ))}
                </ol>
              </nav>
            ) : null}

            <dl className="mt-auto hidden grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 pt-2 text-xs text-muted-foreground md:grid" data-testid="viewer-shortcuts">
              <dt className="flex items-center gap-1"><Kbd>←</Kbd><Kbd>→</Kbd></dt>
              <dd>Cita anterior o siguiente</dd>
              <dt className="flex items-center gap-1"><Kbd>↑</Kbd><Kbd>↓</Kbd></dt>
              <dd>Página del fragmento</dd>
              <dt className="flex items-center gap-1"><Kbd>+</Kbd><Kbd>−</Kbd><Kbd>0</Kbd></dt>
              <dd>Acercar, alejar, ajustar</dd>
              <dt className="flex items-center gap-1"><Kbd>Esc</Kbd></dt>
              <dd>Cerrar</dd>
            </dl>
          </aside>
        </div>
      </DialogContent>
    </Dialog>
  )
}
