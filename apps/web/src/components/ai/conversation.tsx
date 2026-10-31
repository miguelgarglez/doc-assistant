"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ArrowDownIcon } from "lucide-react"
import type { ComponentProps } from "react"
import { useCallback, useSyncExternalStore } from "react"
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom"

const motionQuery = "(prefers-reduced-motion: reduce)"
function subscribeMotion(callback: () => void) {
  const media = window.matchMedia(motionQuery)
  media.addEventListener("change", callback)
  return () => media.removeEventListener("change", callback)
}
function useReducedMotion() {
  return useSyncExternalStore(subscribeMotion, () => window.matchMedia(motionQuery).matches, () => true)
}

export type ConversationProps = ComponentProps<typeof StickToBottom>

export function Conversation({ className, ...props }: ConversationProps) {
  const reducedMotion = useReducedMotion()
  return (
    <StickToBottom
      className={cn("relative flex-1 overflow-y-hidden", className)}
      initial={reducedMotion ? "instant" : "smooth"}
      resize={reducedMotion ? "instant" : "smooth"}
      role="log"
      {...props}
    />
  )
}

export type ConversationContentProps = ComponentProps<typeof StickToBottom.Content>

export function ConversationContent({
  className,
  ...props
}: ConversationContentProps) {
  return (
    <StickToBottom.Content
      className={cn("flex flex-col gap-6 p-1", className)}
      {...props}
    />
  )
}

export type ConversationEmptyStateProps = ComponentProps<"div"> & {
  title?: string
  description?: string
  icon?: React.ReactNode
}

export function ConversationEmptyState({
  className,
  title = "Sin mensajes",
  description = "Escribe una pregunta para empezar.",
  icon,
  children,
  ...props
}: ConversationEmptyStateProps) {
  return (
    <div
      className={cn(
        "flex size-full flex-col items-center justify-center gap-3 p-6 text-center",
        className
      )}
      data-testid="ask-empty"
      role="status"
      {...props}
    >
      {children ?? (
        <>
          {icon ? <div className="text-muted-foreground">{icon}</div> : null}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">{title}</h3>
            {description ? (
              <p className="text-sm text-muted-foreground">{description}</p>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}

export type ConversationScrollButtonProps = ComponentProps<typeof Button>

export function ConversationScrollButton({
  className,
  ...props
}: ConversationScrollButtonProps) {
  const reducedMotion = useReducedMotion()
  const { isAtBottom, scrollToBottom } = useStickToBottomContext()

  const handleScrollToBottom = useCallback(() => {
    scrollToBottom(reducedMotion ? "instant" : "smooth")
  }, [scrollToBottom, reducedMotion])

  if (isAtBottom) {
    return null
  }

  return (
    <Button
      className={cn(
        "absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full shadow-[var(--shadow-panel)]",
        className
      )}
      onClick={handleScrollToBottom}
      size="icon"
      type="button"
      variant="outline"
      aria-label="Ir al final"
      {...props}
    >
      <ArrowDownIcon className="size-4" />
    </Button>
  )
}
