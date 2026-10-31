import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** Scrolls inside the shell, so the sidebar never moves. Pages that fit never show a scrollbar. */
export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className={cn("mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-4 py-5 sm:px-6", className)}>{children}</div>
    </div>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div className="flex min-w-0 flex-col gap-1">
        <h1 className="font-heading text-xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  )
}
