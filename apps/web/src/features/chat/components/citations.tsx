"use client"

import { FileTextIcon } from "lucide-react"

import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationQuote,
  InlineCitationSource,
} from "@/components/ai-elements/inline-citation"
import { Source, Sources, SourcesContent, SourcesTrigger } from "@/components/ai-elements/sources"
import type { Citation } from "@/lib/api/types"
import { citationLabel } from "@/features/chat/lib/citation-label"

type CitationsProps = {
  citations: Citation[]
  activeIndex: number | null
  onOpen: (index: number) => void
  /** Numbered pills before the list. Only needed when the answer carries no inline markers. */
  pills: boolean
}

/** The cited sources as a collapsible list, plus numbered pills when the answer has no inline markers. */
export function Citations({ citations, activeIndex, onOpen, pills }: CitationsProps) {
  if (citations.length === 0) return null
  return (
    <div className="flex flex-col gap-1" data-testid="citations">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {pills ? (
          <InlineCitation className="gap-1.5" role="group" aria-label="Citas de la respuesta">
            {citations.map((citation, index) => (
              <InlineCitationCard key={`${citation.chunk_id}-${index}`}>
                <InlineCitationCardTrigger
                  active={activeIndex === index}
                  aria-label={`Ver cita ${index + 1}: ${citationLabel(citation)}`}
                  data-testid={`citation-${index + 1}`}
                  onClick={() => onOpen(index)}
                >
                  {index + 1}
                </InlineCitationCardTrigger>
                <InlineCitationCardBody>
                  <InlineCitationSource description={citationLabel(citation)} title={citation.doc} />
                  <InlineCitationQuote>{citation.quote}</InlineCitationQuote>
                </InlineCitationCardBody>
              </InlineCitationCard>
            ))}
          </InlineCitation>
        ) : null}
        <Sources>
          <SourcesTrigger count={citations.length} />
          <SourcesContent className="mt-1 gap-0.5">
            {citations.map((citation, index) => (
              <Source
                aria-label={`Abrir fuente ${index + 1}: ${citationLabel(citation)}`}
                key={`${citation.chunk_id}-${index}`}
                onClick={() => onOpen(index)}
              >
                <FileTextIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-medium">
                    <span className="mr-1.5 font-mono text-xs text-muted-foreground tabular-nums">{index + 1}</span>
                    {citationLabel(citation)}
                  </span>
                  <span className="line-clamp-2 text-xs text-muted-foreground">{citation.quote}</span>
                </span>
              </Source>
            ))}
          </SourcesContent>
        </Sources>
      </div>
    </div>
  )
}
