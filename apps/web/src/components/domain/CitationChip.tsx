"use client"

import { Badge } from "@/components/ui/badge"
import { citationPage } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"

type CitationChipProps = {
  citation: Citation
  selected?: boolean
  onSelect: (citation: Citation) => void
}

export function CitationChip({
  citation,
  selected = false,
  onSelect,
}: CitationChipProps) {
  const page = citationPage(citation)
  const pageLabel = page === undefined ? null : ` · p. ${page}`
  const label = `${citation.doc}${citation.section ? ` — ${citation.section}` : ""}`

  return (
    <Badge
      variant={selected ? "default" : "secondary"}
      render={
        <button
          type="button"
          onClick={() => onSelect(citation)}
          aria-pressed={selected}
          aria-label={`Ver fuente: ${label}${pageLabel ?? ""}`}
        />
      }
      className="cursor-pointer font-mono text-xs focus-visible:outline-none"
    >
      {label}
      {pageLabel}
    </Badge>
  )
}
