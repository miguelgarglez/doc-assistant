import type {
  AskMessage,
  Citation,
  ClarificationData,
  RefusalData,
  ResultData,
  StepData,
  Suggestion,
} from "./types"

export type AssistantView =
  | { kind: "pending"; steps: StepData[] }
  | { kind: "provisional"; text: string; steps: StepData[] }
  | { kind: "answer"; text: string; citations: Citation[]; result: ResultData; steps: StepData[] }
  | { kind: "refusal"; refusal: RefusalData; steps: StepData[] }
  | { kind: "clarification"; clarification: ClarificationData; steps: StepData[] }
  | { kind: "failed"; code: string | null; message: string; steps: StepData[] }
  | { kind: "stopped"; steps: StepData[] }

/**
 * One place that decides what an assistant message looks like.
 * `live` is true while this message is the one being generated.
 */
export function viewOfAssistant(message: AskMessage, live: boolean, error?: Error): AssistantView {
  let text = ""
  let citations: Citation[] = []
  let result: ResultData | null = null
  let refusal: RefusalData | null = null
  let clarification: ClarificationData | null = null
  let failure: { code: string; message: string } | null = null
  const steps: StepData[] = []
  for (const part of message.parts) {
    if (part.type === "text") text += part.text
    else if (part.type === "data-step") steps.push(part.data)
    else if (part.type === "data-citations") citations = part.data
    else if (part.type === "data-result") result = part.data
    else if (part.type === "data-refusal") refusal = part.data
    else if (part.type === "data-clarification") clarification = part.data
    else if (part.type === "data-failure") failure = part.data
  }
  if (clarification) return { kind: "clarification", clarification, steps }
  if (refusal) return { kind: "refusal", refusal, steps }
  if (result) return { kind: "answer", text, citations, result, steps }
  if (failure) return { kind: "failed", code: failure.code, message: failure.message, steps }
  if (live) return text ? { kind: "provisional", text, steps } : { kind: "pending", steps }
  if (error) return { kind: "failed", code: null, message: error.message, steps }
  return { kind: "stopped", steps }
}

export function userText(message: AskMessage): string {
  return message.parts.flatMap((part) => (part.type === "text" ? [part.text] : [])).join("")
}

export function lastQuestion(messages: AskMessage[]): string | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role === "user") return userText(message)
  }
  return null
}

/** The most recent assistant message that produced step events: the "last request" of the system page. */
export function lastTrace(messages: AskMessage[]): { question: string | null; steps: StepData[]; total: number | null } | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.role !== "assistant") continue
    const view = viewOfAssistant(message, false)
    if (view.steps.length === 0) continue
    const result = view.kind === "answer" ? view.result : null
    return {
      question: lastQuestion(messages.slice(0, i)),
      steps: view.steps,
      total: result?.timings.total ?? null,
    }
  }
  return null
}

export function suggestionLabel(suggestion: Suggestion): string {
  const section = suggestion.section.replaceAll("_", " ")
  const heading = suggestion.heading?.replaceAll("_", " ")
  if (!heading || heading === section) return `${suggestion.doc} · ${section}`
  return heading.startsWith(section) ? `${suggestion.doc} · ${heading}` : `${suggestion.doc} · ${section} ${heading}`
}
