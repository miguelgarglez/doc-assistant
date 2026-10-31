import createClient, { type Middleware } from "openapi-fetch"

import type { paths } from "@/lib/api/schema"

const REQUEST_TIMEOUT_MS = 180_000

function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  )
}

// Un fallo de red o un timeout se convierte en el mismo contrato de error
// {code, message} que devuelve el API: ningún hook se queda "cargando".
// AbortError se repropaga para que cancelar deje de ser un "network_error".
const networkErrors: Middleware = {
  onError({ error }) {
    if (isAbortError(error)) {
      throw error
    }
    const timeout =
      error instanceof DOMException && error.name === "TimeoutError"
    return Response.json(
      timeout
        ? { code: "timeout", message: "El servicio tardó demasiado en responder." }
        : { code: "network_error", message: "No se pudo contactar con el servicio." },
      { status: 503 }
    )
  },
}

export const api = createClient<paths>({
  baseUrl: "/api",
  fetch: (request: Request) => {
    const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    const signal =
      request.signal && !request.signal.aborted
        ? AbortSignal.any([timeout, request.signal])
        : timeout
    return fetch(request, { signal })
  },
})
api.use(networkErrors)
