import { FileSearchIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

type RefusalNoticeProps = {
  /** Texto redactado por el API (`answer`); el código `reason` es solo diagnóstico. */
  message: string
  reason: string
}

export function RefusalNotice({ message, reason }: RefusalNoticeProps) {
  return (
    <Alert data-testid="refusal-notice">
      <FileSearchIcon />
      <AlertTitle>Sin evidencia suficiente</AlertTitle>
      <AlertDescription>
        <span className="flex flex-col gap-2">
          <span>{message}</span>
          <span className="text-muted-foreground">
            No hay evidencia en los documentos indexados; no se inventa una
            respuesta.
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            motivo: {reason}
          </span>
        </span>
      </AlertDescription>
    </Alert>
  )
}
