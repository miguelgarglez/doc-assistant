import { FileSearchIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

type RefusalNoticeProps = {
  reason: string
}

export function RefusalNotice({ reason }: RefusalNoticeProps) {
  return (
    <Alert data-testid="refusal-notice">
      <FileSearchIcon />
      <AlertTitle>Sin evidencia suficiente</AlertTitle>
      <AlertDescription>
        <span className="flex flex-col gap-2">
          <span>{reason}</span>
          <span className="text-muted-foreground">
            No hay evidencia en los documentos indexados; no se inventa una
            respuesta.
          </span>
        </span>
      </AlertDescription>
    </Alert>
  )
}
