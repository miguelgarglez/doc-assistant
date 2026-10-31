import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

type RefusalNoticeProps = {
  reason: string
}

export function RefusalNotice({ reason }: RefusalNoticeProps) {
  return (
    <Alert variant="destructive" data-testid="refusal-notice">
      <AlertCircleIcon />
      <AlertTitle>Consulta rechazada</AlertTitle>
      <AlertDescription>
        <span className="flex flex-col gap-1">
          <span>{reason}</span>
        </span>
      </AlertDescription>
    </Alert>
  )
}
