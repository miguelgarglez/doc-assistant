"use client"

import { CitationChip } from "@/components/domain/CitationChip"
import type { Citation } from "@/lib/api/types"

type CitationChipsProps = {
  citations: readonly Citation[]
  selectedChunkId?: string | null
  onSelect: (citation: Citation) => void
}

export function CitationChips({
  citations,
  selectedChunkId = null,
  onSelect,
}: CitationChipsProps) {
  if (citations.length === 0) {
    return null
  }

  return (
    <div
      className="flex flex-wrap gap-2"
      role="group"
      aria-label="Citas de la respuesta"
    >
      {citations.map((citation) => (
        <CitationChip
          key={citation.chunk_id}
          citation={citation}
          selected={citation.chunk_id === selectedChunkId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}
