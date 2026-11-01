"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { SHORTCUTS, VIEWER_SHORTCUTS, type ShortcutHelp } from "@/lib/shortcuts"

export function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent data-testid="shortcuts-help" className="max-w-md">
        <DialogHeader>
          <DialogTitle>Atajos de teclado</DialogTitle>
          <DialogDescription className="sr-only">Lista de atajos disponibles en la aplicación.</DialogDescription>
        </DialogHeader>
        <ShortcutList items={SHORTCUTS} />
        <h3 className="mt-1 font-heading text-sm font-semibold">Visor de fuentes</h3>
        <ShortcutList items={VIEWER_SHORTCUTS} />
        <h3 className="mt-1 font-heading text-sm font-semibold">Revisión de avisos</h3>
        <ShortcutList items={[
          { keys: "j / k", action: "Aviso siguiente / anterior" },
          { keys: "a", action: "Marcar revisado cuando esté confirmado" },
          { keys: "d", action: "Descartar aviso" },
        ]} />
      </DialogContent>
    </Dialog>
  )
}

function ShortcutList({ items }: { items: readonly ShortcutHelp[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li className="flex items-baseline justify-between gap-4 text-sm" key={item.keys}>
          <kbd className="rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">{item.keys}</kbd>
          <span className="text-right text-muted-foreground">{item.action}</span>
        </li>
      ))}
    </ul>
  )
}
