import type { UIMessageChunk } from "ai"

import type {
  AskDataParts,
  BlocksData,
  Citation,
  Clarification,
  DoneEvent,
  StepData,
  StreamEvent,
  Suggestion,
} from "./types"

export type AskChunk = UIMessageChunk<unknown, AskDataParts>

const TEXT_ID = "answer"

/**
 * Maps the service stream onto AI SDK UI message chunks, one event at a time.
 *
 * Tokens are provisional until `done`. They are written inside an SDK "step" so a
 * `refusal` with `retract: true` can remove them with `reset-step`. After the reset the
 * step data parts are written again, because the reset removes every part of the step.
 * On `done` the text part always ends up equal to `done.answer`.
 */
export class ChunkMapper {
  private steps = new Map<string, StepData>()
  private stepOpen = false
  private textOpen = false
  private text = ""
  private finished = false
  private suggestions: Suggestion[] = []
  private clarified = false

  push(event: StreamEvent): AskChunk[] {
    if (this.finished) return []
    switch (event.event) {
      case "step":
        return [this.stepChunk(toStep(event))]
      case "token":
        return this.token(event.text)
      case "citations":
        return [citationsChunk(event.citations)]
      case "blocks":
        return [blocksChunk({ blocks_version: event.blocks_version, blocks: event.blocks, follow_ups: event.follow_ups ?? [] })]
      case "refusal":
        return this.refuse(event.answer, event.reason, event.suggestions ?? [], event.retract)
      case "clarification":
        return this.clarify(event.reason, event.clarification)
      case "done":
        return this.done(event)
      case "error":
        return this.fail(event.code, event.message)
    }
  }

  /** The connection closed without a terminal event. */
  truncated(): AskChunk[] {
    return this.fail("stream_truncated", "La respuesta terminó antes de completarse.")
  }

  private stepChunk(step: StepData): AskChunk {
    this.steps.set(step.id, step)
    return { type: "data-step", id: step.id, data: step }
  }

  private replaySteps(): AskChunk[] {
    return [...this.steps.values()].map((step) => ({ type: "data-step", id: step.id, data: step }))
  }

  private token(text: string): AskChunk[] {
    const out: AskChunk[] = []
    if (!this.stepOpen) {
      this.stepOpen = true
      out.push({ type: "start-step" })
    }
    if (!this.textOpen) {
      this.textOpen = true
      out.push({ type: "text-start", id: TEXT_ID })
    }
    this.text += text
    out.push({ type: "text-delta", id: TEXT_ID, delta: text })
    return out
  }

  private closeText(): AskChunk[] {
    if (!this.textOpen) return []
    this.textOpen = false
    return [{ type: "text-end", id: TEXT_ID }]
  }

  private closeStep(): AskChunk[] {
    if (!this.stepOpen) return []
    this.stepOpen = false
    return [{ type: "finish-step" }]
  }

  private refuse(answer: string, reason: string, incoming: Suggestion[], retract: boolean): AskChunk[] {
    // `refusal` and `done` both carry the suggestions; an empty list in the second must not erase the first.
    const suggestions = incoming.length > 0 ? incoming : this.suggestions
    this.suggestions = suggestions
    const out = this.closeText()
    if (retract && this.stepOpen) {
      out.push({ type: "reset-step" }, ...this.replaySteps())
    }
    this.text = ""
    out.push({ type: "data-refusal", id: "refusal", data: { answer, reason, suggestions } })
    return out
  }

  /** An ambiguous question: the user picks a candidate. It is not a refusal, so it never carries suggestions. */
  private clarify(reason: string, clarification: Clarification): AskChunk[] {
    if (this.clarified) return []
    this.clarified = true
    const out = this.closeText()
    if (this.stepOpen) out.push({ type: "reset-step" }, ...this.replaySteps())
    this.text = ""
    out.push({ type: "data-clarification", id: "clarification", data: { reason, clarification } })
    return out
  }

  private done(event: DoneEvent): AskChunk[] {
    if (!event.ok && event.clarification) {
      const out = [...this.clarify(event.reason, event.clarification), ...this.closeStep(), { type: "finish" } as AskChunk]
      this.finished = true
      return out
    }
    if (!event.ok) {
      const out = this.refuse(event.answer, event.reason, event.suggestions ?? [], true)
      out.push(...this.closeStep(), { type: "finish" })
      this.finished = true
      return out
    }
    const out = this.closeText()
    if (this.text !== event.answer) {
      if (this.stepOpen) out.push({ type: "reset-step" }, ...this.replaySteps())
      out.push(
        { type: "text-start", id: TEXT_ID },
        { type: "text-delta", id: TEXT_ID, delta: event.answer },
        { type: "text-end", id: TEXT_ID }
      )
    }
    out.push(
      citationsChunk(event.citations),
      blocksChunk({ blocks_version: event.blocks_version, blocks: event.blocks ?? [], follow_ups: event.follow_ups ?? [] }),
      {
        type: "data-result",
        id: "result",
        data: {
          ok: true,
          reason: event.reason,
          suggestions: event.suggestions ?? [],
          timings: event.timings,
          segments: event.segments ?? [],
        },
      },
      ...this.closeStep(),
      { type: "finish" }
    )
    this.finished = true
    return out
  }

  private fail(code: string, message: string): AskChunk[] {
    const out = [
      ...this.closeText(),
      ...this.closeStep(),
      { type: "data-failure", id: "failure", data: { code, message } } as AskChunk,
      { type: "error", errorText: message } as AskChunk,
    ]
    this.finished = true
    return out
  }
}

function toStep(event: Extract<StreamEvent, { event: "step" }>): StepData {
  return {
    id: event.id,
    status: event.status,
    label: event.label,
    elapsed_s: event.elapsed_s ?? null,
    data: event.data ?? {},
  }
}

function citationsChunk(citations: Citation[]): AskChunk {
  return { type: "data-citations", id: "citations", data: citations }
}

function blocksChunk(data: BlocksData): AskChunk {
  return { type: "data-blocks", id: "blocks", data }
}
