"use client"

import { AlertCircleIcon, CheckIcon, CopyIcon, FileSearchIcon, RefreshCwIcon } from "lucide-react"
import { memo, useState } from "react"

import { Attachment, AttachmentInfo, AttachmentPreview, Attachments } from "@/components/ai-elements/attachments"
import { Message, MessageAction, MessageActions, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import { Citations } from "@/components/chat/citations"
import { TraceBlock } from "@/components/chat/trace-block"
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/toast"
import { copyText, formatAnswerMarkdown } from "@/lib/clipboard"
import type { AskMessage } from "@/lib/chat/types"
import { suggestionLabel, userText, viewOfAssistant } from "@/lib/chat/view"
import { cn } from "@/lib/utils"

type ChatMessageProps = {
  message: AskMessage
  /** True while this is the message being generated. */
  live: boolean
  isLast: boolean
  error?: Error
  activeCitation: number | null
  onOpenCitation: (messageId: string, index: number) => void
  onRegenerate: () => void
  onAsk: (question: string) => void
}

const hoverReveal =
  "transition-opacity duration-150 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 focus-within:opacity-100"

function UserMessage({ message }: { message: AskMessage }) {
  const files = message.parts.flatMap((part) => (part.type === "file" ? [part] : []))
  return (
    <Message from="user" data-testid="user-message">
      {files.length > 0 ? (
        <Attachments className="justify-end">
          {files.map((file, index) => (
            <Attachment
              data={{ id: `${message.id}-${index}`, filename: file.filename ?? "archivo", mediaType: file.mediaType, url: file.url || undefined }}
              key={index}
            >
              <AttachmentPreview />
              <AttachmentInfo />
            </Attachment>
          ))}
        </Attachments>
      ) : null}
      <MessageContent>
        <p className="whitespace-pre-wrap break-words">{userText(message)}</p>
      </MessageContent>
    </Message>
  )
}

function RefusalCard({ answer, reason }: { answer: string; reason: string }) {
  return (
    <aside
      className="flex gap-3 rounded-xl border border-[color:var(--refusal-border)] bg-[color:var(--refusal-bg)] p-4 text-[color:var(--refusal-fg)]"
      data-testid="refusal-notice"
      role="status"
    >
      <FileSearchIcon aria-hidden className="mt-0.5 size-5 shrink-0 opacity-80" />
      <div className="flex min-w-0 flex-col gap-1.5">
        <h3 className="font-heading text-sm font-medium">Sin evidencia suficiente</h3>
        <p className="text-sm leading-relaxed">{answer}</p>
        <p className="text-sm leading-relaxed opacity-80">
          No hay evidencia en los documentos indexados; no se inventa una respuesta.
        </p>
        <p className="font-mono text-xs opacity-75">motivo: {reason}</p>
      </div>
    </aside>
  )
}

function AssistantMessage({ message, live, isLast, error, activeCitation, onOpenCitation, onRegenerate, onAsk }: ChatMessageProps) {
  const { toast } = useToast()
  const [copied, setCopied] = useState(false)
  const view = viewOfAssistant(message, live, error)
  const total = view.kind === "answer" ? (view.result.timings.total ?? null) : null

  async function copy() {
    if (view.kind !== "answer") return
    if (await copyText(formatAnswerMarkdown(view.text, view.citations))) {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } else {
      toast("No se pudo copiar")
    }
  }

  const suggestions =
    view.kind === "refusal"
      ? view.refusal.suggestions
      : view.kind === "answer"
        ? view.result.suggestions
        : []

  return (
    <Message from="assistant" data-testid="assistant-message">
      <MessageContent>
        <TraceBlock live={live} steps={view.steps} total={total} />

        {view.kind === "pending" && view.steps.length === 0 ? (
          <p aria-live="polite" className="text-sm" role="status">
            <Shimmer>Pensando…</Shimmer>
          </p>
        ) : null}

        {view.kind === "provisional" ? (
          <div className="flex flex-col gap-2" data-testid="provisional" role="status">
            <div className="text-muted-foreground opacity-70">
              <MessageResponse isAnimating>{view.text}</MessageResponse>
            </div>
            <p className="text-xs">
              <Shimmer>Verificando la respuesta con las fuentes…</Shimmer>
            </p>
          </div>
        ) : null}

        {view.kind === "answer" ? (
          <>
            <div data-testid="answer-text">
              <MessageResponse>{view.text}</MessageResponse>
            </div>
            <Citations
              activeIndex={activeCitation}
              citations={view.citations}
              onOpen={(index) => onOpenCitation(message.id, index)}
            />
          </>
        ) : null}

        {view.kind === "refusal" ? <RefusalCard answer={view.refusal.answer} reason={view.refusal.reason} /> : null}

        {view.kind === "failed" ? (
          <Alert data-testid="ask-error-notice" variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>{view.code ? `Error (${view.code})` : "Error"}</AlertTitle>
            <AlertDescription>{view.message}</AlertDescription>
            {isLast ? (
              <AlertAction>
                <Button onClick={onRegenerate} size="sm" variant="outline">
                  Reintentar
                </Button>
              </AlertAction>
            ) : null}
          </Alert>
        ) : null}

        {view.kind === "stopped" ? (
          <p className="text-sm text-muted-foreground" data-testid="ask-cancelled">
            Respuesta detenida.
            {isLast ? (
              <Button className="ml-2" onClick={onRegenerate} size="sm" variant="outline">
                Reintentar
              </Button>
            ) : null}
          </p>
        ) : null}

        {suggestions.length > 0 && isLast ? (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-muted-foreground">Prueba con</p>
            <Suggestions>
              {suggestions.map((item) => (
                <Suggestion
                  key={`${item.doc_id}-${item.section}`}
                  onClick={onAsk}
                  suggestion={`¿Qué dice ${item.doc} sobre ${item.heading ?? `la sección ${item.section}`}?`}
                >
                  {suggestionLabel(item)}
                </Suggestion>
              ))}
            </Suggestions>
          </div>
        ) : null}
      </MessageContent>

      {view.kind === "answer" ? (
        <MessageActions className={cn("-ml-1.5", !isLast && hoverReveal)}>
          <MessageAction label={copied ? "Copiado" : "Copiar respuesta"} onClick={() => void copy()}>
            {copied ? <CheckIcon /> : <CopyIcon />}
          </MessageAction>
          {isLast ? (
            <MessageAction label="Regenerar respuesta" onClick={onRegenerate}>
              <RefreshCwIcon />
            </MessageAction>
          ) : null}
        </MessageActions>
      ) : null}
    </Message>
  )
}

export const ChatMessage = memo(function ChatMessage(props: ChatMessageProps) {
  return props.message.role === "user" ? <UserMessage message={props.message} /> : <AssistantMessage {...props} />
})
