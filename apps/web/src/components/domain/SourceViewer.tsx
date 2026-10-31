"use client"

import { useEffect, useRef } from "react"

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
}

export function SourceViewer({
  citation,
  pageImageSrc,
  page,
}: SourceViewerProps) {
  const regionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (citation && regionRef.current) {
      regionRef.current.focus()
    }
  }, [citation])

  if (!citation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fuente</CardTitle>
          <CardDescription>
            Selecciona una cita para ver el fragmento y la página.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fuente</CardTitle>
        <CardDescription>
          {citation.doc}
          {citation.section ? ` · ${citation.section}` : ""}
          {page !== null ? ` · p. ${page}` : ""}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          ref={regionRef}
          tabIndex={-1}
          role="region"
          aria-label={`Fuente ${citation.doc}${page !== null ? `, página ${page}` : ""}`}
          className="flex flex-col gap-4 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {pageImageSrc ? (
            // eslint-disable-next-line @next/next/no-img-element -- PNG dinámico del proxy BFF
            <img
              src={pageImageSrc}
              alt={`Página ${page ?? ""} de ${citation.doc}`}
              width={480}
              height={280}
              className="h-auto max-h-72 w-full rounded-md border border-border bg-muted object-contain object-top"
            />
          ) : null}
          <Separator />
          <ScrollArea className="max-h-48 pr-3">
            <p className="text-sm leading-relaxed text-foreground">
              <HighlightedFragment
                fragment={citation.fragment}
                quote={citation.quote}
              />
            </p>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  )
}
