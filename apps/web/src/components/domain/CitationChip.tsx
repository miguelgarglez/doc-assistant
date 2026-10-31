import { Badge } from "@/components/ui/badge"
import type { Citation } from "@/lib/domain/types"

type CitationChipProps = {
  citation: Citation
}

export function CitationChip({ citation }: CitationChipProps) {
  const pageLabel =
    citation.page === undefined ? null : ` · p. ${citation.page}`

  return (
    <Badge variant="secondary" title={citation.sourceId}>
      {citation.label}
      {pageLabel}
    </Badge>
  )
}
