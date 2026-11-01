"use client"

import { Chat, useChat } from "@ai-sdk/react"
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react"

import { useUploads } from "@/components/providers/uploads-provider"
import { useQuestionHistory } from "@/hooks/use-question-history"
import { AskTransport } from "@/lib/chat/transport"
import type { AskMessage } from "@/lib/chat/types"
import { lastTrace, lastQuestion } from "@/lib/chat/view"

const STORAGE_KEY = "doc-assistant.conversation.v1"
const CONVERSATION_KEY = "doc-assistant.conversation-id.v1"

type ChatContextValue = {
  messages: AskMessage[]
  status: "submitted" | "streaming" | "ready" | "error"
  error: Error | undefined
  busy: boolean
  ask: (question: string) => void
  regenerate: () => void
  stop: () => void
  clear: () => void
  conversationId: () => string
  history: ReturnType<typeof useQuestionHistory>
  trace: ReturnType<typeof lastTrace>
}

const ChatContext = createContext<ChatContextValue | null>(null)

function restore(): AskMessage[] {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as AskMessage[]) : []
  } catch {
    return []
  }
}

class ConversationIdentity {
  private id: string | null = null

  get(): string {
    if (!this.id) {
      try {
        this.id = window.sessionStorage.getItem(CONVERSATION_KEY)
      } catch {
        // A blocked session store does not prevent a new conversation.
      }
      this.id ||= crypto.randomUUID()
      try {
        window.sessionStorage.setItem(CONVERSATION_KEY, this.id)
      } catch {
        // The identity remains available for this page session.
      }
    }
    return this.id
  }

  clear() {
    this.id = null
    try {
      window.sessionStorage.removeItem(CONVERSATION_KEY)
    } catch {
      // Nothing persisted to remove.
    }
  }
}

/** The session conversation lives in one `Chat` so it survives route changes and reloads of the tab. */
export function ChatProvider({ children }: { children: ReactNode }) {
  const { chat, identity } = useMemo(() => {
    const identity = new ConversationIdentity()
    const chat = new Chat<AskMessage>({ transport: new AskTransport("/api", () => identity.get()) })
    return { chat, identity }
  }, [])
  const { messages, status, error, sendMessage, regenerate, stop, setMessages } = useChat<AskMessage>({ chat })
  const { markAttached, items } = useUploads()
  const history = useQuestionHistory()
  const restored = useRef(false)

  useEffect(() => {
    if (restored.current) return
    restored.current = true
    const saved = restore()
    if (saved.length > 0) setMessages(saved)
  }, [setMessages])

  useEffect(() => {
    if (!restored.current || status === "streaming" || status === "submitted") return
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // Storage full or blocked: the conversation stays in memory.
    }
  }, [messages, status])

  const ask = useCallback(
    (question: string) => {
      const text = question.trim()
      if (!text) return
      history.push(text)
      const attached = items.filter((item) => item.origin === "chat" && !item.attached && item.status !== "error")
      markAttached(attached.map((item) => item.id))
      void sendMessage({
        text,
        files: attached.map((item) => ({
          type: "file" as const,
          mediaType: item.file.type || "application/octet-stream",
          filename: item.name,
          url: item.previewUrl ?? "",
        })),
      })
    },
    [history, items, markAttached, sendMessage]
  )
  const retry = useCallback(() => {
    if (lastQuestion(messages)) void regenerate()
  }, [messages, regenerate])
  const clear = useCallback(() => {
    void stop()
    setMessages([])
    identity.clear()
    try {
      window.sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // Nothing persisted to remove.
    }
  }, [identity, setMessages, stop])

  const busy = status === "submitted" || status === "streaming"
  const trace = useMemo(() => lastTrace(messages), [messages])
  const getConversationId = useCallback(() => identity.get(), [identity])

  const value = useMemo<ChatContextValue>(
    () => ({ messages, status, error, busy, ask, regenerate: retry, stop: () => void stop(), clear, conversationId: getConversationId, history, trace }),
    [messages, status, error, busy, ask, retry, stop, clear, getConversationId, history, trace]
  )
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useConversation() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error("ChatProvider missing")
  return ctx
}
