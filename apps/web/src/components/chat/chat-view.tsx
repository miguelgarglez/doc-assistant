"use client"

import { useEffect, useMemo, useState } from "react"
import { useStickToBottomContext } from "use-stick-to-bottom"

import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Message, MessageContent } from "@/components/ai-elements/message"
import { usePromptInput } from "@/components/ai-elements/prompt-input"
import { AssistantMessage } from "@/components/chat/assistant-message"
import { Composer } from "@/components/chat/composer"
import { EmptyState } from "@/components/chat/empty-state"
import { SourceViewer } from "@/components/chat/source-viewer"
import { UserMessage } from "@/components/chat/user-message"
import { useConversation } from "@/components/providers/chat-provider"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"
import { useMediaQuery } from "@/hooks/use-media-query"
import type { Citation } from "@/lib/chat/types"
import { viewOfAssistant } from "@/lib/chat/view"

type ViewerState = { messageId: string; index: number }

function ScrollOnSend({ count, lastRole }: { count: number; lastRole: string | undefined }) {
  const { scrollToBottom } = useStickToBottomContext()
  useEffect(() => {
    if (lastRole === "user") void scrollToBottom("smooth")
  }, [count, lastRole, scrollToBottom])
  return null
}

export function ChatView() {
  const { messages, status, error, busy, ask, regenerate, stop } = useConversation()
  const { textareaRef } = usePromptInput()
  const [viewer, setViewer] = useState<ViewerState | null>(null)
  const wide = useMediaQuery("(min-width: 1024px)")

  useEffect(() => {
    if (window.matchMedia("(pointer: fine)").matches) textareaRef.current?.focus()
  }, [textareaRef])

  const viewerCitations = useMemo<Citation[]>(() => {
    const message = viewer ? messages.find((item) => item.id === viewer.messageId) : undefined
    if (!message) return []
    const view = viewOfAssistant(message, false)
    return view.kind === "answer" ? view.citations : []
  }, [messages, viewer])
  const viewerOpen = viewer !== null && viewerCitations.length > 0

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || event.isComposing) return
      if (viewerOpen) setViewer(null)
      else if (busy) stop()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [busy, stop, viewerOpen])

  const send = (question: string) => {
    setViewer(null)
    ask(question)
  }
  const retry = () => {
    setViewer(null)
    regenerate()
  }

  const last = messages.at(-1)
  const awaitingAssistant = status === "submitted" && last?.role === "user"
  // Stopped before the service answered anything: there is no assistant message to say so.
  const stoppedEarly = !busy && last?.role === "user"

  return (
    <div className="flex min-h-0 flex-1" data-testid="chat-view">
      <div className="flex min-w-0 flex-1 flex-col">
        <h1 className="sr-only">Chat</h1>
        {messages.length === 0 ? (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <EmptyState onAsk={send} />
          </div>
        ) : (
          <Conversation>
            <ConversationContent data-testid="thread">
              {messages.map((message, index) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AssistantMessage
                    activeCitation={viewer?.messageId === message.id ? viewer.index : null}
                    error={error}
                    isLast={index === messages.length - 1}
                    key={message.id}
                    live={busy && index === messages.length - 1}
                    message={message}
                    onAsk={send}
                    onOpenCitation={(citationIndex) => setViewer({ messageId: message.id, index: citationIndex })}
                    onRetry={retry}
                  />
                )
              )}
              {stoppedEarly ? (
                <Message from="assistant">
                  <MessageContent>
                    <p className="flex items-center gap-2 text-sm text-muted-foreground" data-testid="ask-cancelled">
                      Respuesta detenida.
                      <Button onClick={retry} size="sm" type="button" variant="ghost">
                        Reintentar
                      </Button>
                    </p>
                  </MessageContent>
                </Message>
              ) : null}
              {awaitingAssistant ? (
                <Message from="assistant">
                  <MessageContent>
                    <p className="text-sm" role="status">
                      <Shimmer>Buscando en las fuentes…</Shimmer>
                    </p>
                  </MessageContent>
                </Message>
              ) : null}
            </ConversationContent>
            <ConversationScrollButton />
            <ScrollOnSend count={messages.length} lastRole={last?.role} />
          </Conversation>
        )}
        <div className="mx-auto w-full max-w-3xl shrink-0 px-4 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">
          <Composer />
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Las respuestas se verifican contra los fragmentos indexados.
          </p>
        </div>
      </div>

      {viewerOpen && wide ? (
        <aside aria-label="Fuente citada" className="hidden w-[24rem] shrink-0 border-l border-border lg:block xl:w-[26rem]">
          <SourceViewer
            citations={viewerCitations}
            index={Math.min(viewer.index, viewerCitations.length - 1)}
            onClose={() => setViewer(null)}
            onIndexChange={(index) => setViewer({ messageId: viewer.messageId, index })}
          />
        </aside>
      ) : null}
      {!wide ? (
        <Sheet open={viewerOpen} onOpenChange={(open) => !open && setViewer(null)}>
          <SheetContent className="h-[85dvh] gap-0 rounded-t-xl p-0" showCloseButton={false} side="bottom">
            <SheetTitle className="sr-only">Fuente citada</SheetTitle>
            <SheetDescription className="sr-only">Página y fragmento de la cita seleccionada.</SheetDescription>
            {viewerOpen ? (
              <SourceViewer
                citations={viewerCitations}
                index={Math.min(viewer.index, viewerCitations.length - 1)}
                onClose={() => setViewer(null)}
                onIndexChange={(index) => setViewer({ messageId: viewer.messageId, index })}
              />
            ) : null}
          </SheetContent>
        </Sheet>
      ) : null}
    </div>
  )
}
