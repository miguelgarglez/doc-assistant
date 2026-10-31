"use client"

import { Button } from "@/components/ui/button"
import { SHORTCUTS } from "@/lib/shortcuts"

type ShortcutsHelpProps = {
  open: boolean
  onClose: () => void
}

export function ShortcutsHelp({ open, onClose }: ShortcutsHelpProps) {
  if (!open) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/30 p-4 sm:items-center"
      role="presentation"
      onClick={onClose}
      data-testid="shortcuts-overlay"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
        className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-[var(--shadow-panel)] outline-none"
        onClick={(event) => event.stopPropagation()}
        data-testid="shortcuts-help"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 id="shortcuts-title" className="text-base font-medium">
            Atajos de teclado
          </h2>
          <Button type="button" size="sm" variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
        </div>
        <ul className="flex flex-col gap-2">
          {SHORTCUTS.map((item) => (
            <li
              key={item.keys}
              className="flex items-baseline justify-between gap-4 text-sm"
            >
              <kbd className="rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">
                {item.keys}
              </kbd>
              <span className="text-right text-muted-foreground">
                {item.action}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
