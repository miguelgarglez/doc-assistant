import type { ReactNode } from "react"

import { SidebarTrigger } from "@/components/ui/sidebar"

/** Top bar of every page: sidebar toggle (the only way to open the nav on mobile), title, page actions. */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-background/80 px-3 backdrop-blur sm:px-4">
      <SidebarTrigger />
      <div className="flex min-w-0 flex-1 items-baseline gap-3">
        <h1 className="truncate font-heading text-sm font-semibold">{title}</h1>
        {description ? (
          <p className="hidden truncate text-xs text-muted-foreground md:block">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-1.5">{actions}</div> : null}
    </header>
  )
}
