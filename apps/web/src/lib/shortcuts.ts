import type { KeyboardEvent as ReactKeyboardEvent } from "react"

export type ShortcutHelp = {
  keys: string
  action: string
}

export const SHORTCUTS: readonly ShortcutHelp[] = [
  { keys: "Enter", action: "Enviar la pregunta" },
  { keys: "Shift+Enter", action: "Nueva línea" },
  { keys: "⌘/Ctrl+K", action: "Ir al campo de pregunta" },
  { keys: "Esc", action: "Detener la respuesta" },
  { keys: "↑ / ↓", action: "Recorrer preguntas anteriores (campo vacío)" },
  { keys: "⌘/Ctrl+V", action: "Pegar un PDF o una imagen como fuente" },
  { keys: "⌘/Ctrl+B", action: "Mostrar u ocultar el menú" },
  { keys: "? o ⌘/Ctrl+/", action: "Mostrar esta ayuda" },
]

export const VIEWER_SHORTCUTS: readonly ShortcutHelp[] = [
  { keys: "← / →", action: "Cita anterior o siguiente" },
  { keys: "↑ / ↓", action: "Página anterior o siguiente del fragmento" },
  { keys: "+ / −", action: "Acercar o alejar la página" },
  { keys: "0", action: "Ajustar la página a la ventana" },
  { keys: "Esc", action: "Cerrar el visor" },
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
