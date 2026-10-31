import type { ComponentProps } from "react"
import { cn } from "@/lib/utils"

// Adaptado del registro shadcn/ui: trace, sin la parte plegable.
export function Trace({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="trace" className={cn("flex w-full min-w-0 flex-col gap-2", className)} {...props} />
}

export function TraceLine({ className, status, ...props }: ComponentProps<"span"> & { status?: "running" | "error" | "pending" }) {
  return <span data-slot="trace-line" data-status={status} className={cn("flex w-fit max-w-full min-w-0 items-center gap-2 text-sm text-muted-foreground data-[status=error]:text-destructive data-[status=pending]:opacity-60", className)} {...props} />
}

export function TraceTitle({ className, ...props }: ComponentProps<"span">) {
  return <span data-slot="trace-title" className={cn("min-w-0 truncate", className)} {...props} />
}
