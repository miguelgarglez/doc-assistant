"use client"

import { CheckIcon, CopyIcon, RefreshCwIcon } from "lucide-react"
import { memo, useMemo, useState } from "react"
import { toast } from "sonner"

import { Message, MessageAction, MessageActions, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Suggestion } from "@/components/ai-elements/suggestion"
import { AnswerLink } from "@/components/chat/citation-marker"
import { CitationContext } from "@/components/chat/citation-context"
import { ClarificationCard } from "@/components/chat/clarification"
import { Citations } from "@/components/chat/citations"
import { TraceBlock } from "@/components/chat/trace-block"
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { duration } from "@/lib/format"
import { copyText, formatAnswerMarkdown } from "@/lib/clipboard"
import type { AskMessage, Citation, RefusalData, ResultData } from "@/lib/chat/types"
import { clarificationText } from "@/lib/chat/clarification"
import { refusalCopy } from "@/lib/chat/refusal-copy"
import { segmentsMatch, withMarkers } from "@/lib/chat/inline"
import { suggestionLabel, viewOfAssistant, type AssistantView } from "@/lib/chat/view"
import { cn } from "@/lib/utils"

const answerComponents = { a: AnswerLink }

type AssistantMessageProps = {
  message: AskMessage
  live: boolean
  isLast: boolean
  error?: Error
  activeCitation: number | null
  onOpenCitation: (index: number) => void
  onRetry: () => void
  onAsk: (question: string) => void
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  live,
  isLast,
  error,
  activeCitation,
  onOpenCitation,
  onRetry,
  onAsk,
}: AssistantMessageProps) {
  const view = viewOfAssistant(message, live, isLast ? error : undefined)
  const total = view.kind === "answer" ? (view.result.timings.total ?? null) : null

  return (
    <Message data-kind={view.kind} data-testid="assistant-message" from="assistant">
      <MessageContent>
        <TraceBlock live={live} steps={view.steps} total={total} />
        {view.kind === "pending" && view.steps.length === 0 ? (
          <p className="text-sm" role="status">
            <Shimmer>Buscando en las fuentes…</Shimmer>
          </p>
        ) : null}
        {view.kind === "provisional" ? (
          <div data-testid="provisional-answer">
            <div className="text-muted-foreground">
              <MessageResponse isAnimating>{view.text}</MessageResponse>
            </div>
            <p className="mt-2 text-xs" role="status">
              <Shimmer>Verificando con las fuentes…</Shimmer>
            </p>
          </div>
        ) : null}
        {view.kind === "answer" ? (
          <AnswerBody
            activeIndex={activeCitation}
            citations={view.citations}
            onOpen={onOpenCitation}
            segments={view.result.segments}
            text={view.text}
          />
        ) : null}
        {view.kind === "refusal" ? <Refusal onAsk={onAsk} refusal={view.refusal} /> : null}
        {view.kind === "clarification" ? <ClarificationCard data={view.clarification} onAsk={onAsk} /> : null}
        {view.kind === "failed" ? (
          <Alert data-testid="ask-error-notice" variant="destructive">
            <AlertTitle>No se pudo completar la consulta</AlertTitle>
            <AlertDescription>{view.message}</AlertDescription>
            {isLast ? (
              <AlertAction>
                <Button onClick={onRetry} size="sm" type="button" variant="outline">
                  Reintentar
                </Button>
              </AlertAction>
            ) : null}
          </Alert>
        ) : null}
        {view.kind === "stopped" ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground" data-testid="ask-cancelled">
            Respuesta detenida.
            {isLast ? (
              <Button onClick={onRetry} size="sm" type="button" variant="ghost">
                Reintentar
              </Button>
            ) : null}
          </p>
        ) : null}
        {view.kind === "answer" || view.kind === "refusal" || view.kind === "clarification" ? (
          <Actions copyText={copyTextOf(view)} elapsed={total} isLast={isLast} onRetry={onRetry} />
        ) : null}
      </MessageContent>
    </Message>
  )
})

function copyTextOf(view: Extract<AssistantView, { kind: "answer" | "refusal" | "clarification" }>): string {
  if (view.kind === "refusal") {
    const copy = refusalCopy(view.refusal)
    return `${copy.title}. ${copy.body}`
  }
  if (view.kind === "clarification") return clarificationText(view.clarification.clarification)
  return formatAnswerMarkdown(withMarkers(view.text, view.result.segments, view.citations.length, "plain"), view.citations)
}

type AnswerBodyProps = {
  text: string
  segments: ResultData["segments"]
  citations: Citation[]
  activeIndex: number | null
  onOpen: (index: number) => void
}

/** The verified answer. Markers sit after each supported segment; without them the sources follow the text. */
function AnswerBody({ text, segments, citations, activeIndex, onOpen }: AnswerBodyProps) {
  const inline = segmentsMatch(text, segments, citations.length) && segments.some((segment) => segment.refs.length > 0)
  const context = useMemo(() => ({ citations, activeIndex, onOpen }), [citations, activeIndex, onOpen])
  return (
    <CitationContext.Provider value={context}>
      <div data-inline={inline} data-testid="answer-text">
        <MessageResponse components={answerComponents}>
          {inline ? withMarkers(text, segments, citations.length) : text}
        </MessageResponse>
      </div>
      <Citations activeIndex={activeIndex} citations={citations} onOpen={onOpen} pills={!inline} />
    </CitationContext.Provider>
  )
}

function Actions({ copyText: text, elapsed, isLast, onRetry }: { copyText: string; elapsed: number | null; isLast: boolean; onRetry: () => void }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    const ok = await copyText(text)
    if (!ok) {
      toast("No se pudo copiar la respuesta")
      return
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }
  return (
    <MessageActions
      className={cn(
        "-ml-1.5 transition-opacity duration-150",
        !isLast && "[@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100"
      )}
    >
      <MessageAction data-testid="copy-answer" label={copied ? "Copiado" : "Copiar respuesta"} onClick={copy}>
        {copied ? <CheckIcon /> : <CopyIcon />}
      </MessageAction>
      {isLast ? (
        <MessageAction data-testid="regenerate" label="Volver a generar" onClick={onRetry}>
          <RefreshCwIcon />
        </MessageAction>
      ) : null}
      {elapsed === null ? null : <span className="ml-1 text-xs tabular-nums text-muted-foreground">{duration(elapsed)}</span>}
    </MessageActions>
  )
}

export function Refusal({ refusal, onAsk }: { refusal: RefusalData; onAsk: (question: string) => void }) {
  const copy = refusalCopy(refusal)
  return (
    <aside
      aria-live="polite"
      className="flex flex-col gap-2 rounded-xl border border-[color:var(--refusal-border)] bg-[color:var(--refusal-bg)] p-4 text-[color:var(--refusal-fg)]"
      data-testid="refusal-notice"
      role="status"
    >
      <h3 className="font-heading text-sm font-semibold">{copy.title}</h3>
      <p className="text-sm leading-relaxed">{copy.body}</p>
      {refusal.suggestions.length > 0 ? (
        <div className="flex flex-col gap-1.5 pt-1">
          <p className="text-xs font-medium opacity-80">Apartados relacionados</p>
          <div className="flex flex-wrap gap-1.5">
            {refusal.suggestions.map((item) => {
              const topic = item.heading ?? `la sección ${item.section}`
              return (
                <Suggestion
                  className="h-auto max-w-full bg-background/60 py-1 whitespace-normal text-left text-xs"
                  key={`${item.doc_id}-${item.section}`}
                  onClick={onAsk}
                  suggestion={`¿Qué dice ${item.doc} sobre ${topic}?`}
                >
                  {suggestionLabel(item)}
                </Suggestion>
              )
            })}
          </div>
        </div>
      ) : null}
    </aside>
  )
}
