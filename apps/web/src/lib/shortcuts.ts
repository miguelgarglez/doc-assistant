import type { KeyboardEvent as ReactKeyboardEvent } from "react"

export type ShortcutHelp = {
  keys: string
  action: string
}

export const SHORTCUTS: readonly ShortcutHelp[] = [
  { keys: "Enter", action: "Enviar pregunta" },
  { keys: "Shift+Enter", action: "Nueva línea" },
  { keys: "⌘/Ctrl+Enter", action: "Enviar pregunta" },
  { keys: "⌘/Ctrl+K", action: "Enfocar el campo de pregunta" },
  { keys: "Esc", action: "Cancelar generación o cerrar el visor" },
  { keys: "↑ / ↓", action: "Recorrer historial de preguntas (input vacío)" },
  { keys: "?", action: "Mostrar esta ayuda" },
  { keys: "⌘/Ctrl+/", action: "Mostrar esta ayuda" },
]

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tag = target.tagName
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
    return true
  }
  return target.isContentEditable
}

export function isModKey(
  event: KeyboardEvent | ReactKeyboardEvent
): boolean {
  return event.metaKey || event.ctrlKey
}
