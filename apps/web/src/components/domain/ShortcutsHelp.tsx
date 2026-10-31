"use client"

import { Dialog } from "@base-ui/react/dialog"

import { Button } from "@/components/ui/button"
import { SHORTCUTS } from "@/lib/shortcuts"

type ShortcutsHelpProps = {
  open: boolean
  onClose: () => void
}

export function ShortcutsHelp({ open, onClose }: ShortcutsHelpProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-foreground/30" data-testid="shortcuts-overlay" />
        <Dialog.Popup
          className="fixed bottom-4 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-xl border border-border bg-card p-5 shadow-[var(--shadow-panel)] outline-none sm:top-1/2 sm:bottom-auto sm:-translate-y-1/2"
          data-testid="shortcuts-help"
        >
        <div className="mb-4 flex items-start justify-between gap-3">
          <Dialog.Title className="text-base font-medium">
            Atajos de teclado
          </Dialog.Title>
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
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
