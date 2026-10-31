"use client"

import type { ComponentProps } from "react"

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"

export const InlineCitation = ({ className, ...props }: ComponentProps<"span">) => (
  <span className={cn("inline-flex items-center gap-1 align-baseline", className)} {...props} />
)

export const InlineCitationCard = (props: ComponentProps<typeof HoverCard>) => <HoverCard {...props} />

export type InlineCitationCardTriggerProps = ComponentProps<"button"> & {
  active?: boolean
}

/** Numbered pill. Hover or focus shows the card; click is left to the caller (opens the viewer). */
export const InlineCitationCardTrigger = ({
  className,
  active = false,
  children,
  ...props
}: InlineCitationCardTriggerProps) => (
  <HoverCardTrigger
    closeDelay={80}
    delay={120}
    render={
      <button
        className={cn(
          "inline-flex h-5 min-w-5 cursor-pointer items-center justify-center rounded-full border border-border bg-secondary px-1.5 text-[0.6875rem] font-medium tabular-nums text-secondary-foreground transition-[background-color,color,transform] duration-150 ease-[var(--ease-out)] hover:bg-primary hover:text-primary-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none active:scale-[0.94] aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground motion-reduce:active:scale-100",
          className
        )}
        aria-pressed={active}
        type="button"
        {...props}
      />
    }
  >
    {children}
  </HoverCardTrigger>
)

export const InlineCitationCardBody = ({
  className,
  ...props
}: ComponentProps<typeof HoverCardContent>) => (
  <HoverCardContent className={cn("w-80 gap-2 p-3", className)} {...props} />
)

export const InlineCitationSource = ({
  title,
  description,
  className,
  children,
  ...props
}: ComponentProps<"div"> & { title?: string; description?: string }) => (
  <div className={cn("flex flex-col gap-1", className)} {...props}>
    {title ? <h4 className="truncate text-sm leading-tight font-medium">{title}</h4> : null}
    {description ? <p className="truncate text-xs text-muted-foreground">{description}</p> : null}
    {children}
  </div>
)

export const InlineCitationQuote = ({
  children,
  className,
  ...props
}: ComponentProps<"blockquote">) => (
  <blockquote
    className={cn("border-l-2 border-border pl-3 text-sm leading-relaxed text-muted-foreground", className)}
    {...props}
  >
    {children}
  </blockquote>
)
