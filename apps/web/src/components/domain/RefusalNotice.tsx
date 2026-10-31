import { FileSearchIcon } from "lucide-react"

type RefusalNoticeProps = {
  /** Texto redactado por el API (`answer`); el código `reason` es solo diagnóstico. */
  message: string
  reason: string
}

export function RefusalNotice({ message, reason }: RefusalNoticeProps) {
  return (
    <aside
      data-testid="refusal-notice"
      className="rounded-xl border border-[color:var(--refusal-border)] bg-[color:var(--refusal-bg)] p-5 text-[color:var(--refusal-fg)] shadow-[var(--shadow-panel)]"
      role="status"
      aria-live="polite"
    >
      <div className="flex gap-3">
        <FileSearchIcon className="mt-0.5 size-5 shrink-0 opacity-80" aria-hidden />
        <div className="flex min-w-0 flex-col gap-2">
          <h3 className="font-heading text-base font-medium">
            Sin evidencia suficiente
          </h3>
          <p className="text-sm leading-relaxed">{message}</p>
          <p className="text-sm leading-relaxed opacity-80">
            No hay evidencia en los documentos indexados; no se inventa una
            respuesta.
          </p>
          <p className="font-mono text-xs text-current/80">motivo: {reason}</p>
        </div>
      </div>
    </aside>
  )
}
