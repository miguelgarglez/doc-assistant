"use client"

import { useEffect, useState } from "react"

import { fetchHighlight } from "@/lib/api/highlight"
import type { PageHighlight } from "@/lib/api/types"

export type HighlightState =
  | { status: "skipped" }
  | { status: "loading" }
  | { status: "ready"; highlight: PageHighlight }
  | { status: "error" }

type Settled = { key: string; state: HighlightState }

/** Where `quote` sits on a page of a PDF source. `enabled` is false for sources without a page text layer. */
export function useHighlight(sourceId: string, page: number | undefined, quote: string, enabled: boolean): HighlightState {
  const key = `${sourceId}\u0000${page}\u0000${quote}`
  const [settled, setSettled] = useState<Settled | null>(null)

  useEffect(() => {
    if (!enabled || page === undefined) return
    const controller = new AbortController()
    fetchHighlight(sourceId, page, quote, controller.signal).then(
      (highlight) => setSettled({ key, state: { status: "ready", highlight } }),
      () => {
        if (!controller.signal.aborted) setSettled({ key, state: { status: "error" } })
      }
    )
    return () => controller.abort()
  }, [enabled, key, page, quote, sourceId])

  if (!enabled || page === undefined) return { status: "skipped" }
  return settled?.key === key ? settled.state : { status: "loading" }
}
