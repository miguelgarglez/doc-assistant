import type { Segment } from "./types"

/** Link target of a citation marker inside the answer Markdown. The number is 1-based. */
export const CITE_HREF = /^#cite-(\d+)$/

/** Keeps a marker on the line of the word it follows instead of wrapping alone. */
const WORD_JOINER = "\u2060"

const tail = /\s*$/

/** True when the segments are usable: they rebuild the answer exactly and point at real citations. */
export function segmentsMatch(text: string, segments: readonly Segment[], citationCount: number): boolean {
  if (segments.length === 0) return false
  if (segments.map((segment) => segment.text).join("") !== text) return false
  return segments.every((segment) => segment.refs.every((ref) => Number.isInteger(ref) && ref >= 0 && ref < citationCount))
}

/**
 * The answer with a marker after each segment that has citations. `link` markers become
 * clickable buttons in the rendered Markdown, `plain` ones are the `[n]` kept when copying.
 * Without matching segments the text comes back unchanged and the citations stay after it.
 */
export function withMarkers(
  text: string,
  segments: readonly Segment[],
  citationCount: number,
  style: "link" | "plain" = "link"
): string {
  if (!segmentsMatch(text, segments, citationCount)) return text
  return segments
    .map((segment) => {
      if (segment.refs.length === 0) return segment.text
      const space = tail.exec(segment.text)?.[0] ?? ""
      const body = segment.text.slice(0, segment.text.length - space.length)
      const markers = segment.refs
        .map((ref) => (style === "link" ? `[${ref + 1}](#cite-${ref + 1})` : `[${ref + 1}]`))
        .join("")
      return `${body}${style === "link" ? WORD_JOINER : ""}${markers}${space}`
    })
    .join("")
}

/** Citations that no segment points at; they only show in the sources list. */
export function citedRefs(segments: readonly Segment[]): Set<number> {
  return new Set(segments.flatMap((segment) => segment.refs))
}
