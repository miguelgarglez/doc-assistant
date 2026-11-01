"use client"

import { CheckIcon, CopyIcon, RefreshCwIcon } from "lucide-react"
import { memo, useMemo, useState } from "react"
import { toast } from "sonner"

import { Message, MessageAction, MessageActions, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import { FeedbackAction } from "@/features/chat/components/feedback-action"
import { AnswerBlocks } from "@/features/chat/components/answer-blocks"
import { AnswerSkeleton } from "@/features/chat/components/answer-skeleton"
import { AnswerLink } from "@/features/chat/components/citation-marker"
import { CitationContext } from "@/features/chat/components/citation-context"
import { ClarificationCard } from "@/features/chat/components/clarification"
import { Citations } from "@/features/chat/components/citations"
import { TraceBlock } from "@/features/chat/components/trace-block"
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { duration } from "@/lib/format"
import { copyText } from "@/lib/clipboard"
import { answerMarkdown } from "@/features/chat/lib/answer-copy"
import type { AskMessage, Block, Citation, FollowUp, RefusalData, ResultData } from "@/features/chat/lib/types"
import { answerRehypePlugins } from "@/features/chat/components/answer-plugins"
import { clarificationText } from "@/features/chat/lib/clarification"
import { refusalCopy } from "@/features/chat/lib/refusal-copy"
import { segmentsMatch, withMarkers } from "@/features/chat/lib/inline"
import { suggestionLabel, viewOfAssistant, type AssistantView } from "@/features/chat/lib/view"
import { cn } from "@/lib/utils"
import { useMediaQuery } from "@/hooks/use-media-query"

const answerComponents = { a: AnswerLink }

/** Words fade in as they arrive. The global reduced-motion rule turns the fade off. */
const STREAM_ANIMATION = { animation: "fadeIn", duration: 140, easing: "ease-out", stagger: 12, sep: "word" } as const

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
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)")
  const view = viewOfAssistant(message, live, isLast ? error : undefined)
  const requestId = message.parts.find((part) => part.type === "data-request")?.data.request_id
  const total = view.kind === "answer" ? (view.result.timings.total ?? null) : null

  return (
    <Message data-kind={view.kind} data-testid="assistant-message" from="assistant">
      <MessageContent>
        <TraceBlock live={live} steps={view.steps} total={total} />
        {view.kind === "pending" ? (
          <>
            {view.steps.length === 0 ? (
              <p className="text-sm" role="status">
                <Shimmer>Buscando en las fuentes…</Shimmer>
              </p>
            ) : null}
            <AnswerSkeleton />
          </>
        ) : null}
        {view.kind === "provisional" ? (
          <div data-testid="provisional-answer">
            <div className="text-muted-foreground">
              <MessageResponse animated={reducedMotion ? false : STREAM_ANIMATION} isAnimating rehypePlugins={answerRehypePlugins}>
                {view.text}
              </MessageResponse>
            </div>
            <p className="mt-2 text-xs" role="status">
              <Shimmer>Verificando con las fuentes…</Shimmer>
            </p>
          </div>
        ) : null}
        {view.kind === "answer" ? (
          <AnswerBody
            activeIndex={activeCitation}
            blocks={view.blocks}
            citations={view.citations}
            followUps={view.followUps}
            onAsk={onAsk}
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
          <Actions copyText={copyTextOf(view)} elapsed={total} isLast={isLast} onRetry={onRetry} requestId={requestId} />
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
  return answerMarkdown(view)
}

type AnswerBodyProps = {
  text: string
  segments: ResultData["segments"]
  blocks: Block[]
  followUps: FollowUp[]
  onAsk: (question: string) => void
  citations: Citation[]
  activeIndex: number | null
  onOpen: (index: number) => void
}

/**
 * The verified answer. With blocks, the structured view replaces the Markdown body (it says the
 * same, from the same rows); without them, or when they cannot be trusted, the Markdown is shown.
 * Markers sit after each supported segment; without them the sources follow the text.
 */
function AnswerBody({ text, segments, blocks, followUps, onAsk, citations, activeIndex, onOpen }: AnswerBodyProps) {
  const structured = blocks.length > 0
  const inline = structured || (segmentsMatch(text, segments, citations.length) && segments.some((segment) => segment.refs.length > 0))
  const context = useMemo(() => ({ citations, activeIndex, onOpen }), [citations, activeIndex, onOpen])
  return (
    <CitationContext.Provider value={context}>
      <div data-inline={inline} data-structured={structured} data-testid="answer-text">
        {structured ? (
          <AnswerBlocks blocks={blocks} onAsk={onAsk} />
        ) : (
          <MessageResponse components={answerComponents} rehypePlugins={answerRehypePlugins}>
            {inline ? withMarkers(text, segments, citations.length) : text}
          </MessageResponse>
        )}
      </div>
      <Citations activeIndex={activeIndex} citations={citations} onOpen={onOpen} pills={!inline} />
      <FollowUps items={followUps} onAsk={onAsk} />
    </CitationContext.Provider>
  )
}

/** Questions the service can answer from what it found. Alt+1..3 asks them. */
function FollowUps({ items, onAsk }: { items: FollowUp[]; onAsk: (question: string) => void }) {
  if (items.length === 0) return null
  return (
    <Suggestions aria-label="Preguntas sugeridas" className="gap-1.5" data-testid="follow-ups">
      {items.slice(0, 3).map((item, index) => (
        <Suggestion
          aria-keyshortcuts={`Alt+${index + 1}`}
          className="h-auto max-w-full py-1 whitespace-normal text-left text-xs"
          data-testid="follow-up"
          key={item.question}
          onClick={onAsk}
          suggestion={item.question}
          title={item.question}
        >
          {item.label}
        </Suggestion>
      ))}
    </Suggestions>
  )
}

function Actions({ copyText: text, elapsed, isLast, onRetry, requestId }: { copyText: string; elapsed: number | null; isLast: boolean; onRetry: () => void; requestId?: string }) {
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
      {requestId ? <FeedbackAction requestId={requestId} /> : null}
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
