"use client"

import type { ComponentProps } from "react"
import { useCallback } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** Chips wrap instead of scrolling sideways: a hidden scroller hides the suggestions it exists to show. */
export const Suggestions = ({ className, ...props }: ComponentProps<"div">) => (
  <div className={cn("flex flex-wrap items-center gap-2", className)} role="group" {...props} />
)

export type SuggestionProps = Omit<ComponentProps<typeof Button>, "onClick"> & {
  suggestion: string
  onClick?: (suggestion: string) => void
}

export const Suggestion = ({
  suggestion,
  onClick,
  className,
  variant = "outline",
  size = "sm",
  children,
  ...props
}: SuggestionProps) => {
  const handleClick = useCallback(() => onClick?.(suggestion), [onClick, suggestion])
  return (
    <Button
      className={cn("cursor-pointer rounded-full px-3.5", className)}
      onClick={handleClick}
      size={size}
      type="button"
      variant={variant}
      {...props}
    >
      {children || suggestion}
    </Button>
  )
}
