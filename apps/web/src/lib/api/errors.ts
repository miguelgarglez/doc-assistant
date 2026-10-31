import type { ErrorBody, HTTPValidationError } from "@/lib/api/types"

function isErrorBody(value: unknown): value is ErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "code" in value &&
    "message" in value &&
    typeof (value as ErrorBody).code === "string" &&
    typeof (value as ErrorBody).message === "string"
  )
}

function isValidationError(value: unknown): value is HTTPValidationError {
  return typeof value === "object" && value !== null && "detail" in value
}

export function toErrorBody(error: unknown): ErrorBody {
  if (isErrorBody(error)) {
    return error
  }
  if (isValidationError(error)) {
    const first = error.detail?.[0]
    return {
      code: "validation_error",
      message: first?.msg ?? "La solicitud no es válida.",
    }
  }
  return {
    code: "unknown_error",
    message: "No se pudo completar la consulta.",
  }
}
