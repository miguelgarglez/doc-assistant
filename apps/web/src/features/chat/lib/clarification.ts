import { formatAmountEs } from "@/lib/domain/format-amount"

import type { Clarification, ClarificationCandidate } from "./types"

const PLAIN_AMOUNT = /^-?\d+(\.\d+)?$/

/** A stored amount shown the Spanish way; text in any other format is shown as stored. */
export function candidateTotal(candidate: ClarificationCandidate): string | null {
  if (!candidate.total) return null
  return PLAIN_AMOUNT.test(candidate.total) ? formatAmountEs(candidate.total) : candidate.total
}

/** "De Emisor para Cliente", with only the parties the invoice has. */
export function candidateParties(candidate: ClarificationCandidate): string | null {
  const parts = [
    candidate.emisor ? `De ${candidate.emisor}` : null,
    candidate.cliente ? `${candidate.emisor ? "para" : "Para"} ${candidate.cliente}` : null,
  ].filter(Boolean)
  return parts.length > 0 ? parts.join(" ") : null
}

/** The accessible name of a candidate: the number first, then every field it has. */
export function candidateName(candidate: ClarificationCandidate): string {
  const fields = [
    candidate.emisor ? `emisor ${candidate.emisor}` : null,
    candidate.cliente ? `cliente ${candidate.cliente}` : null,
    candidate.fecha ? `fecha ${candidate.fecha}` : null,
    candidateTotal(candidate) ? `total ${candidateTotal(candidate)}` : null,
  ].filter(Boolean)
  return [`Factura ${candidate.doc}`, ...fields].join(", ")
}

/** How many matching invoices the list leaves out. */
export function hiddenCandidates(clarification: Clarification): number {
  return Math.max(0, clarification.total - clarification.candidates.length)
}

export function clarificationText(clarification: Clarification): string {
  const lines = clarification.candidates.map((candidate) => `- ${candidateName(candidate)}`)
  return [clarification.prompt, clarification.detail, ...lines].filter(Boolean).join("\n")
}
