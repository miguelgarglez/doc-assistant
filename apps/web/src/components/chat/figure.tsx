import type { Cell } from "@/lib/chat/types"
import { cn } from "@/lib/utils"

const BASE = "whitespace-nowrap tabular-nums"

/** A stored value. Amounts and dates are chips with tabular figures so columns of them line up; the number never splits from its symbol. */
export function Figure({ cell, className }: { cell: Pick<Cell, "text" | "kind">; className?: string }) {
  if (cell.text === null || cell.text === undefined) {
    return (
      <span aria-label="sin dato" className={cn("text-muted-foreground", className)} data-kind="empty">
        <span aria-hidden>—</span>
      </span>
    )
  }
  switch (cell.kind) {
    case "amount":
    case "percent":
      return (
        <span className={cn(BASE, "rounded-md bg-muted px-1.5 py-0.5 font-medium text-foreground", className)} data-figure={cell.kind}>
          {cell.text}
        </span>
      )
    case "date":
      return (
        <span className={cn(BASE, "rounded-md bg-muted/70 px-1.5 py-0.5 text-foreground", className)} data-figure="date">
          {cell.text}
        </span>
      )
    case "id":
      return (
        <span className={cn(BASE, "font-mono text-[0.8125rem] text-foreground", className)} data-figure="id">
          {cell.text}
        </span>
      )
    default:
      return <span className={className}>{cell.text}</span>
  }
}
