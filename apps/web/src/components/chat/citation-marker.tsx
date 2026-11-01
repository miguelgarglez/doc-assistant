"use client"

import type { ComponentProps } from "react"

import { useCitations } from "@/components/chat/citation-context"
import {
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationQuote,
  InlineCitationSource,
} from "@/components/ai-elements/inline-citation"
import { citationLabel, citationLocation } from "@/lib/chat/citation-label"
import { CITE_HREF } from "@/lib/chat/inline"

/** The numbered marker of a citation. `number` is 1-based. */
export function CitationMarker({ number }: { number: number }) {
  const context = useCitations()
  const citation = context?.citations[number - 1]
  if (!context || !citation) return <span>{number}</span>
  return (
    <InlineCitationCard>
      <InlineCitationCardTrigger
        active={context.activeIndex === number - 1}
        aria-label={`Cita ${number}: ${citationLabel(citation)}`}
        className="mx-px h-[1.125rem] min-w-[1.125rem] rounded-md px-1 align-[0.12em] text-[0.6875rem] leading-none"
        data-testid={`citation-marker-${number}`}
        onClick={() => context.onOpen(number - 1)}
      >
        {number}
      </InlineCitationCardTrigger>
      <InlineCitationCardBody>
        <InlineCitationSource description={citationLocation(citation)} title={citation.doc} />
        <InlineCitationQuote>{citation.quote}</InlineCitationQuote>
      </InlineCitationCardBody>
    </InlineCitationCard>
  )
}

/** Markdown link override: `#cite-n` becomes a marker, anything else stays an ordinary link. */
export function AnswerLink({ href, children }: ComponentProps<"a">) {
  const match = href ? CITE_HREF.exec(href) : null
  if (match) return <CitationMarker number={Number(match[1])} />
  return (
    <a className="font-medium underline underline-offset-4" href={href} rel="noreferrer noopener" target="_blank">
      {children}
    </a>
  )
}
