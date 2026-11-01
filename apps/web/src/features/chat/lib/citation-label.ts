import { citationPage } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"

/** "§ section · p. 3": where in the document the citation sits. */
export function citationLocation(citation: Citation): string {
  const page = citationPage(citation)
  const pages = citation.pages.length > 1 ? `pp. ${citation.pages[0]}–${citation.pages.at(-1)}` : page === undefined ? "" : `p. ${page}`
  return [citation.section ? `§ ${citation.section}` : null, pages || null].filter(Boolean).join(" · ")
}

/** "doc · § section · p. 3", the one-line name of a citation. */
export function citationLabel(citation: Citation): string {
  return [citation.doc, citationLocation(citation) || null].filter(Boolean).join(" · ")
}
