const AI_SERVICE_URL =
  process.env.AI_SERVICE_URL ?? "http://127.0.0.1:8000"

// Solo estas cabeceras llegan al servicio de IA (sin cookies ni Authorization).
const FORWARDED_REQUEST_HEADERS = ["content-type", "accept", "accept-language"]

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
  "content-length",
  "content-encoding",
])

type RouteContext = {
  params: Promise<{ path: string[] }>
}

async function proxyRequest(request: Request, context: RouteContext) {
  const { path } = await context.params
  const base = new URL(ensureTrailingSlash(AI_SERVICE_URL))
  // Cada segmento se recodifica: un segmento como "http%3A%2F%2Fx" no puede
  // convertirse en URL absoluta ni salir del servicio de IA (SSRF).
  const target = new URL(path.map(encodeURIComponent).join("/"), base)
  if (target.origin !== base.origin || !target.pathname.startsWith(base.pathname)) {
    return Response.json(
      { code: "invalid_path", message: "Ruta no permitida" },
      { status: 400 },
    )
  }
  target.search = new URL(request.url).search

  const headers = new Headers()
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name)
    if (value) headers.set(name, value)
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
    signal: request.signal,
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer()
  }

  let upstream: Response
  try {
    upstream = await fetch(target, init)
  } catch {
    return Response.json(
      { code: "upstream_unavailable", message: "El servicio de IA no responde" },
      { status: 502 },
    )
  }
  const responseHeaders = new Headers()
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      responseHeaders.set(key, value)
    }
  })

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  })
}

function ensureTrailingSlash(url: string) {
  return url.endsWith("/") ? url : `${url}/`
}

export function GET(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}

export function POST(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}

export function PUT(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}

export function PATCH(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}

export function DELETE(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}

export function OPTIONS(request: Request, context: RouteContext) {
  return proxyRequest(request, context)
}
