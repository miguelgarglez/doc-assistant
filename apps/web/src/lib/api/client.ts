import createClient, { type Middleware } from "openapi-fetch"

import type { paths } from "@/lib/api/schema"

const REQUEST_TIMEOUT_MS = 180_000

// Un fallo de red o un timeout se convierte en el mismo contrato de error
// {code, message} que devuelve el API: ningún hook se queda "cargando".
const networkErrors: Middleware = {
  onError({ error }) {
    const timeout = error instanceof DOMException && error.name === "TimeoutError"
    return Response.json(
      timeout
        ? { code: "timeout", message: "El servicio tardó demasiado en responder." }
        : { code: "network_error", message: "No se pudo contactar con el servicio." },
      { status: 503 },
    )
  },
}

export const api = createClient<paths>({
  baseUrl: "/api",
  fetch: (request: Request) =>
    fetch(request, { signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) }),
})
api.use(networkErrors)
