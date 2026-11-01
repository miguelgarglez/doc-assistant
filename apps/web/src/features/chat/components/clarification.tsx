"use client"

import { useId, type KeyboardEvent } from "react"

import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item"
import {
  candidateName,
  candidateParties,
  candidateTotal,
  hiddenCandidates,
} from "@/features/chat/lib/clarification"
import type { ClarificationData } from "@/features/chat/lib/types"

const MOVES: Record<string, (index: number, last: number) => number> = {
  ArrowDown: (index, last) => Math.min(index + 1, last),
  ArrowUp: (index) => Math.max(index - 1, 0),
  Home: () => 0,
  End: (_, last) => last,
}

/** Arrow keys, Home and End move between the candidates; Tab still reaches each one. */
function moveFocus(event: KeyboardEvent<HTMLDivElement>) {
  const move = MOVES[event.key]
  if (!move) return
  const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button"))
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
  if (index === -1) return
  event.preventDefault()
  buttons[move(index, buttons.length - 1)]?.focus()
}

type ClarificationCardProps = {
  data: ClarificationData
  onAsk: (question: string) => void
}

/** The question is ambiguous: the real candidates are buttons, and a click asks again with the choice made. */
export function ClarificationCard({ data, onAsk }: ClarificationCardProps) {
  const { clarification } = data
  const headingId = useId()
  const hidden = hiddenCandidates(clarification)
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border border-primary/25 bg-card p-4 text-card-foreground"
      data-testid="clarification-notice"
    >
      <div className="flex flex-col gap-1" role="status">
        <h3 className="font-heading text-sm font-semibold" id={headingId}>
          {clarification.prompt}
        </h3>
        {clarification.detail ? <p className="text-sm leading-relaxed text-muted-foreground">{clarification.detail}</p> : null}
      </div>
      <ItemGroup aria-labelledby={headingId} className="gap-1.5" onKeyDown={moveFocus} role="group">
        {clarification.candidates.map((candidate) => {
          const parties = candidateParties(candidate)
          const total = candidateTotal(candidate)
          return (
            <Item
              aria-label={candidateName(candidate)}
              className="cursor-pointer flex-nowrap text-left transition-[color,background-color,border-color,box-shadow,transform] duration-150 ease-[var(--ease-out)] active:scale-[0.985] motion-reduce:active:scale-100 [@media(hover:hover)]:hover:border-primary/40 [@media(hover:hover)]:hover:bg-muted"
              data-testid="clarification-candidate"
              key={candidate.doc_id}
              onClick={() => onAsk(candidate.question)}
              render={<button type="button" />}
              size="sm"
              variant="outline"
            >
              <ItemContent className="min-w-0 gap-0.5">
                <ItemTitle className="max-w-full gap-x-2">
                  <span className="truncate">{candidate.doc}</span>
                  {candidate.fecha ? <span className="shrink-0 font-normal text-muted-foreground">{candidate.fecha}</span> : null}
                </ItemTitle>
                {parties ? <ItemDescription>{parties}</ItemDescription> : null}
              </ItemContent>
              {total ? (
                <ItemActions className="shrink-0 text-sm font-medium tabular-nums">{total}</ItemActions>
              ) : null}
            </Item>
          )
        })}
      </ItemGroup>
      {hidden > 0 ? (
        <p className="text-xs text-muted-foreground">
          {hidden === 1 ? "Hay 1 factura más." : `Hay ${hidden} facturas más.`} Indica el número o la fecha en la pregunta.
        </p>
      ) : null}
    </section>
  )
}
