import type { components } from "@/lib/api/schema"
import type { AskMessage } from "./types"

type Answer = components["schemas"]["AskResponse"]

/** Reconstruct the conversation from traces captured by the local service. */
export function messagesFromHistory(items: unknown[]): AskMessage[] {
  const messages: AskMessage[] = []
  for (const value of [...items].reverse()) {
    if (!value || typeof value !== "object" || !("question" in value) || typeof value.question !== "string") continue
    if (!("request_id" in value) || typeof value.request_id !== "string") continue
    const requestId = value.request_id
    messages.push({ id: `${requestId}-question`, role: "user", parts: [{ type: "text", text: value.question }] })
    if (!("result" in value) || !value.result || typeof value.result !== "object") continue
    const raw = value.result
    if (!("ok" in raw) || typeof raw.ok !== "boolean" || !("answer" in raw) || typeof raw.answer !== "string") continue
    const result = raw as Answer
    const parts: AskMessage["parts"] = [{ type: "data-request", id: "request", data: { request_id: requestId } }]
    if (result.ok) {
      parts.push(
        { type: "text", text: result.answer },
        { type: "data-citations", id: "citations", data: result.citations ?? [] },
        { type: "data-blocks", id: "blocks", data: { blocks_version: result.blocks_version, blocks: result.blocks ?? [], follow_ups: result.follow_ups ?? [] } },
        { type: "data-result", id: "result", data: { ok: true, reason: result.reason ?? "", suggestions: result.suggestions ?? [], timings: {}, segments: result.segments ?? [] } },
      )
    } else if (result.clarification) {
      parts.push({ type: "data-clarification", id: "clarification", data: { reason: result.reason, clarification: result.clarification } })
    } else {
      parts.push({ type: "data-refusal", id: "refusal", data: { answer: result.answer, reason: result.reason, suggestions: result.suggestions ?? [] } })
    }
    messages.push({ id: `${requestId}-answer`, role: "assistant", parts })
  }
  return messages
}
