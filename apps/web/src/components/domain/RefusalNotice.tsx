import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { Refusal } from "@/lib/domain/types"

type RefusalNoticeProps = {
  refusal: Refusal
}

export function RefusalNotice({ refusal }: RefusalNoticeProps) {
  return (
    <Alert variant="destructive">
      <AlertCircleIcon />
      <AlertTitle>Consulta rechazada</AlertTitle>
      <AlertDescription>
        <span className="flex flex-col gap-1">
          <span>{refusal.reason}</span>
          <span>{refusal.guidance}</span>
        </span>
      </AlertDescription>
    </Alert>
  )
}
