import type { components } from "@/lib/api/schema"
import { readSse } from "@/lib/api/sse"

export type IngestStageEvent = components["schemas"]["IngestStageEvent"]
export type IngestStage = IngestStageEvent["stage"]

function parseStage(data: string): IngestStageEvent | null {
  try {
    const value: unknown = JSON.parse(data)
    if (typeof value === "object" && value !== null && "stage" in value && "label" in value) return value as IngestStageEvent
  } catch {
    return null
  }
  return null
}

/**
 * Follows the stages of an upload being processed. Progress is cosmetic, the upload response stays
 * the source of truth, so a missing or broken stream just ends quietly.
 */
export async function followIngestJob(jobId: string, onStage: (event: IngestStageEvent) => void, signal: AbortSignal): Promise<void> {
  try {
    const response = await fetch(`/api/ingest/jobs/${encodeURIComponent(jobId)}/events`, {
      headers: { accept: "text/event-stream" },
      signal,
    })
    if (!response.ok || !response.body) return
    for await (const frame of readSse(response.body)) {
      if (frame.event !== "stage") continue
      const event = parseStage(frame.data)
      if (!event) continue
      onStage(event)
      if (event.stage === "done" || event.stage === "error") return
    }
  } catch {
    return
  }
}
