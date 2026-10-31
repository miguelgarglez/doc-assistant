import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import type { ErrorBody } from "@/lib/api/types"

type AskErrorNoticeProps = {
  error: ErrorBody
  onRetry?: () => void
}

export function AskErrorNotice({ error, onRetry }: AskErrorNoticeProps) {
  return (
    <Alert
      variant="destructive"
      data-testid={
        error.code === "cancelled" ? "ask-cancelled" : "ask-error-notice"
      }
    >
      <AlertCircleIcon />
      <AlertTitle>
        {error.code === "cancelled" ? "Cancelada" : `Error (${error.code})`}
      </AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
      {onRetry ? (
        <AlertAction>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Reintentar
          </Button>
        </AlertAction>
      ) : null}
    </Alert>
  )
}
