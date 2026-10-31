import { api } from "@/lib/api/client"
import type { PageHighlight } from "@/lib/api/types"

const cache = new Map<string, PageHighlight>()

/** Rectangles where `quote` sits on a page of a PDF source. Answers are cached per source, page and quote. */
export async function fetchHighlight(sourceId: string, page: number, quote: string, signal?: AbortSignal): Promise<PageHighlight> {
  const key = `${sourceId}\u0000${page}\u0000${quote}`
  const hit = cache.get(key)
  if (hit) return hit
  const { data } = await api.GET("/sources/{source_id}/pages/{n}/highlight", {
    params: { path: { source_id: sourceId, n: page }, query: { quote } },
    signal,
  })
  if (!data) throw new Error("highlight_unavailable")
  cache.set(key, data)
  return data
}
