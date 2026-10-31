"use client"

import { ChevronLeftIcon, ChevronRightIcon, XIcon, ZoomInIcon, ZoomOutIcon } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { citationPage, sourcePageUrl } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"
import { HighlightedFragment } from "@/lib/domain/highlight-fragment"
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
  className?: string
}

/** Cited page and fragment. Lives beside the thread on wide screens and inside a sheet on narrow ones. */
export function SourceViewer({ citations, index, onIndexChange, onClose, className }: SourceViewerProps) {
  const citation = citations[index]
  const [pageIndexByChunk, setPageIndexByChunk] = useState<Record<string, number>>({})
  const [zoomed, setZoomed] = useState(false)
  if (!citation) return null

  const pageIndex = Math.min(pageIndexByChunk[citation.chunk_id] ?? 0, Math.max(citation.pages.length - 1, 0))
  const page = citationPage(citation, pageIndex)
  const setPage = (next: number) => setPageIndexByChunk((current) => ({ ...current, [citation.chunk_id]: next }))

  return (
    <section
      aria-label={`Fuente ${citation.doc}${page === undefined ? "" : `, página ${page}`}`}
      className={cn("flex h-full min-h-0 flex-col bg-card", className)}
      data-testid="source-viewer"
    >
      <header className="flex shrink-0 items-start gap-2 border-b border-border p-3">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-heading text-sm font-semibold">{citation.doc}</h2>
          <p className="truncate font-mono text-xs text-muted-foreground">
            {citation.section ? `Sección ${citation.section}` : "Fragmento"}
            {page === undefined ? "" : ` · p. ${page}`}
          </p>
        </div>
        {citations.length > 1 ? (
          <div aria-label="Navegación entre citas" className="flex shrink-0 items-center gap-0.5" role="group">
            <Button
              aria-label="Cita anterior"
              disabled={index <= 0}
              onClick={() => onIndexChange(index - 1)}
              size="icon-sm"
              variant="ghost"
            >
              <ChevronLeftIcon />
            </Button>
            <span className="min-w-9 text-center font-mono text-xs tabular-nums text-muted-foreground">
              {index + 1}/{citations.length}
            </span>
            <Button
              aria-label="Cita siguiente"
              disabled={index >= citations.length - 1}
              onClick={() => onIndexChange(index + 1)}
              size="icon-sm"
              variant="ghost"
            >
              <ChevronRightIcon />
            </Button>
          </div>
        ) : null}
        <Button aria-label="Cerrar visor" onClick={onClose} size="icon-sm" variant="ghost">
          <XIcon />
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium text-muted-foreground">Fragmento citado</p>
            <p className="text-sm leading-relaxed" data-testid="viewer-fragment">
              <HighlightedFragment fragment={fragmentBody(citation.fragment)} quote={citation.quote} />
            </p>
          </div>
          {page !== undefined ? (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">Página original</p>
                {citation.pages.length > 1 ? (
                  <div aria-label="Páginas del fragmento" className="flex items-center gap-0.5" role="group">
                    <Button
                      aria-label="Página anterior del fragmento"
                      disabled={pageIndex <= 0}
                      onClick={() => setPage(pageIndex - 1)}
                      size="icon-xs"
                      variant="ghost"
                    >
                      <ChevronLeftIcon />
                    </Button>
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {pageIndex + 1}/{citation.pages.length}
                    </span>
                    <Button
                      aria-label="Página siguiente del fragmento"
                      disabled={pageIndex >= citation.pages.length - 1}
                      onClick={() => setPage(pageIndex + 1)}
                      size="icon-xs"
                      variant="ghost"
                    >
                      <ChevronRightIcon />
                    </Button>
                  </div>
                ) : null}
              </div>
              <button
                aria-label={zoomed ? "Reducir página de fuente" : "Ampliar página de fuente"}
                aria-pressed={zoomed}
                className={cn(
                  "group relative block w-full overflow-hidden rounded-md border border-border bg-muted outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                  zoomed ? "cursor-zoom-out" : "cursor-zoom-in"
                )}
                data-testid="source-page-zoom"
                onClick={() => setZoomed((current) => !current)}
                type="button"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- PNG dinámico del proxy */}
                <img
                  alt={`Página ${page} de ${citation.doc}`}
                  className={cn("mx-auto h-auto w-full object-contain object-top", !zoomed && "max-h-72")}
                  src={sourcePageUrl(citation.doc_id, page)}
                />
                <span className="pointer-events-none absolute right-2 bottom-2 grid size-6 place-items-center rounded-md border border-border bg-card/90 text-muted-foreground">
                  {zoomed ? <ZoomOutIcon className="size-3.5" /> : <ZoomInIcon className="size-3.5" />}
                </span>
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
