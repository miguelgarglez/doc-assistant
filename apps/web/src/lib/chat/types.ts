import type { UIMessage } from "ai"

import type { components } from "../api/schema"

export type Citation = components["schemas"]["Citation"]
export type Suggestion = components["schemas"]["Suggestion"]
export type Segment = components["schemas"]["Segment"]
export type Clarification = components["schemas"]["Clarification"]
export type ClarificationCandidate = components["schemas"]["ClarificationCandidate"]
export type StepEvent = components["schemas"]["StepEvent"]
export type DoneEvent = components["schemas"]["DoneEvent"]
export type StreamEvent = components["schemas"]["StreamEvent"]

export type StepId = StepEvent["id"]

export type StepData = {
  id: StepId
  status: StepEvent["status"]
  label: string
  elapsed_s: number | null
  data: Record<string, unknown>
}

export type ResultData = {
  ok: boolean
  reason: string
  suggestions: Suggestion[]
  timings: Record<string, number>
  /** Pieces of the answer with the citations that support them; empty when markers are not possible. */
  segments: Segment[]
}

export type RefusalData = {
  answer: string
  reason: string
  suggestions: Suggestion[]
}

export type ClarificationData = { reason: string; clarification: Clarification }

export type FailureData = { code: string; message: string }

/**
 * Data parts of the assistant message. Text parts carry the answer tokens. Everything the
 * service sends besides tokens travels as a typed data part, so the UI never parses text.
 */
export type AskDataParts = {
  step: StepData
  citations: Citation[]
  result: ResultData
  refusal: RefusalData
  clarification: ClarificationData
  failure: FailureData
}

export type AskMessage = UIMessage<never, AskDataParts>
