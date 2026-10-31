import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { ErrorBody } from "@/lib/api/types"

type AskErrorNoticeProps = {
  error: ErrorBody
}

export function AskErrorNotice({ error }: AskErrorNoticeProps) {
  return (
    <Alert variant="destructive" data-testid="ask-error-notice">
      <AlertCircleIcon />
      <AlertTitle>Error ({error.code})</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  )
}
