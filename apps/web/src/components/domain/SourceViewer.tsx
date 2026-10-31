"use client"

import { useState } from "react"
import { ChevronLeftIcon, ChevronRightIcon, ZoomInIcon, ZoomOutIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { HighlightedFragment } from "@/lib/domain/highlight-fragment"
import type { Citation } from "@/lib/api/types"

type SourceViewerProps = {
  citation: Citation | null
  pageImageSrc: string | null
  page: number | null
  citationIndex?: number
  citationCount?: number
  onPrevCitation?: () => void
  onNextCitation?: () => void
}

export function SourceViewer({
  citation,
  pageImageSrc,
  page,
  citationIndex = 0,
  citationCount = 0,
  onPrevCitation,
  onNextCitation,
}: SourceViewerProps) {
  const [zoomedChunkId, setZoomedChunkId] = useState<string | null>(null)
  const zoomed = citation !== null && zoomedChunkId === citation.chunk_id

  if (!citation) {
    return (
      <Card data-testid="source-viewer-empty">
        <CardHeader>
          <CardTitle>Fuente</CardTitle>
          <CardDescription>
            Selecciona una cita para ver la página y el fragmento citado.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const showNav = citationCount > 1 && onPrevCitation && onNextCitation

  return (
    <Card data-testid="source-viewer">
      <CardHeader className="gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <CardTitle>Fuente</CardTitle>
            <CardDescription className="font-mono text-xs">
              <span>{citation.doc}</span>
              {citation.section ? <span>{` · ${citation.section}`}</span> : null}
              {page !== null ? <span>{` · p. ${page}`}</span> : null}
            </CardDescription>
          </div>
          {showNav ? (
            <div
              className="flex shrink-0 items-center gap-1"
              role="group"
              aria-label="Navegación entre citas"
            >
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                onClick={onPrevCitation}
                disabled={citationIndex <= 0}
                aria-label="Cita anterior"
              >
                <ChevronLeftIcon />
              </Button>
              <span className="min-w-10 text-center font-mono text-xs text-muted-foreground">
                {citationIndex + 1}/{citationCount}
              </span>
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                onClick={onNextCitation}
                disabled={citationIndex >= citationCount - 1}
                aria-label="Cita siguiente"
              >
                <ChevronRightIcon />
              </Button>
            </div>
          ) : null}
        </div>
        <p className="font-mono text-[0.7rem] text-muted-foreground">
          chunk_id: {citation.chunk_id}
        </p>
      </CardHeader>
      <CardContent>
        <div
          aria-live="polite"
          role="region"
          aria-label={`Fuente ${citation.doc}${page !== null ? `, página ${page}` : ""}`}
          className="flex flex-col gap-4 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {pageImageSrc ? (
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() =>
                  setZoomedChunkId((current) =>
                    current === citation.chunk_id ? null : citation.chunk_id
                  )
                }
                className="group relative overflow-hidden rounded-md border border-border bg-muted text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                aria-pressed={zoomed}
                aria-label={
                  zoomed
                    ? "Reducir página de fuente"
                    : "Ampliar página de fuente"
                }
                data-testid="source-page-zoom"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- PNG dinámico del proxy BFF */}
                <img
                  src={pageImageSrc}
                  alt={`Página ${page ?? ""} de ${citation.doc}`}
                  width={480}
                  height={640}
                  className={
                    zoomed
                      ? "h-auto w-full object-contain object-top"
                      : "mx-auto h-auto max-h-80 w-full object-contain object-top"
                  }
                />
                <span className="pointer-events-none absolute right-2 bottom-2 inline-flex items-center gap-1 rounded-md border border-border bg-card/90 px-2 py-1 text-xs text-muted-foreground">
                  {zoomed ? (
                    <ZoomOutIcon className="size-3.5" />
                  ) : (
                    <ZoomInIcon className="size-3.5" />
                  )}
                  {zoomed ? "Clic para reducir" : "Clic para ampliar"}
                </span>
              </button>
            </div>
          ) : null}
          <Separator />
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium text-muted-foreground">
              Fragmento citado
            </p>
            <ScrollArea className="max-h-48 pr-3">
              <p className="text-sm leading-relaxed text-foreground">
                <HighlightedFragment
                  fragment={citation.fragment}
                  quote={citation.quote}
                />
              </p>
            </ScrollArea>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
