"use client"

import { ArrowDownIcon } from "lucide-react"
import { createContext, useContext, useEffect, useState, type ComponentProps, type ReactNode } from "react"
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type ConversationProps = ComponentProps<typeof StickToBottom>

const ScrollAreaContext = createContext<HTMLElement | null>(null)

/** The thread's scroll element, or `null` outside a conversation. Popups portaled out of the thread use it as collision boundary so they never cover what sits below it, like the composer. */
export const useConversationScrollArea = () => useContext(ScrollAreaContext)

function ScrollAreaProvider({ children }: { children: ReactNode }) {
  const { scrollRef } = useStickToBottomContext()
  const [area, setArea] = useState<HTMLElement | null>(null)
  useEffect(() => setArea(scrollRef.current), [scrollRef])
  return <ScrollAreaContext.Provider value={area}>{children}</ScrollAreaContext.Provider>
}

/** The only main scroll area of the chat. `use-stick-to-bottom` keeps the tail in view until the user scrolls up. */
export const Conversation = ({ className, children, ...props }: ConversationProps) => (
  <StickToBottom
    className={cn("relative min-h-0 flex-1 overflow-y-hidden", className)}
    initial="instant"
    resize="smooth"
    role="log"
    aria-label="Conversación"
    {...props}
  >
    {(context) => <ScrollAreaProvider>{typeof children === "function" ? children(context) : children}</ScrollAreaProvider>}
  </StickToBottom>
)

export const ConversationContent = ({
  className,
  ...props
}: ComponentProps<typeof StickToBottom.Content>) => (
  <StickToBottom.Content
    className={cn("mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6", className)}
    {...props}
  />
)

export const ConversationEmptyState = ({
  className,
  ...props
}: ComponentProps<"div">) => (
  <div
    className={cn(
      "mx-auto flex min-h-full w-full max-w-3xl flex-col items-center justify-center gap-6 px-4 py-8 text-center sm:px-6",
      className
    )}
    {...props}
  />
)

export const ConversationScrollButton = ({
  className,
  ...props
}: ComponentProps<typeof Button>) => {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext()
  if (isAtBottom) return null
  return (
    <Button
      aria-label="Ir al final"
      className={cn(
        "absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-background shadow-sm",
        className
      )}
      onClick={() => scrollToBottom()}
      size="icon"
      type="button"
      variant="outline"
      {...props}
    >
      <ArrowDownIcon />
    </Button>
  )
}
