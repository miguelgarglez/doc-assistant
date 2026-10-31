"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { ComponentProps } from "react"

export function Suggestions({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      className={cn("flex flex-wrap gap-2", className)}
      role="group"
      aria-label="Sugerencias"
      {...props}
    />
  )
}

type SuggestionProps = Omit<ComponentProps<typeof Button>, "onClick"> & {
  suggestion: string
  onClick: (suggestion: string) => void
}

export function Suggestion({
  suggestion,
  onClick,
  className,
  ...props
}: SuggestionProps) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className={cn("max-w-full whitespace-normal text-left", className)}
      onClick={() => onClick(suggestion)}
      {...props}
    >
      {suggestion}
    </Button>
  )
}
