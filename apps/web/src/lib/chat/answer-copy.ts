import { formatAnswerMarkdown } from "@/lib/clipboard"
import { tableTsv } from "./blocks"
import { withMarkers } from "./inline"
import type { AssistantView } from "./view"

export type AnswerView = Extract<AssistantView, { kind: "answer" }>

/** The answer as Markdown with `[n]` markers and its citations; always the full text, whatever the blocks show. */
export function answerMarkdown(view: AnswerView): string {
  return formatAnswerMarkdown(withMarkers(view.text, view.result.segments, view.citations.length, "plain"), view.citations)
}

/** The first table of the answer as tab-separated text, or null when it has none. */
export function firstTableTsv(view: AnswerView): string | null {
  const block = view.blocks.find((item) => item.type === "table")
  return block ? tableTsv(block) : null
}
