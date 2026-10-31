"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { SHORTCUTS } from "@/lib/shortcuts"

export function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent data-testid="shortcuts-help" className="max-w-md">
        <DialogHeader>
          <DialogTitle>Atajos de teclado</DialogTitle>
          <DialogDescription className="sr-only">Lista de atajos disponibles en la aplicación.</DialogDescription>
        </DialogHeader>
        <ul className="flex flex-col gap-2">
          {SHORTCUTS.map((item) => (
            <li className="flex items-baseline justify-between gap-4 text-sm" key={item.keys}>
              <kbd className="rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">{item.keys}</kbd>
              <span className="text-right text-muted-foreground">{item.action}</span>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  )
}
