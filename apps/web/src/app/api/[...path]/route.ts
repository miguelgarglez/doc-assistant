const AI_SERVICE_URL =
  process.env.AI_SERVICE_URL ?? "http://127.0.0.1:8000"

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  "expect",
])

type RouteContext = {
  params: Promise<{ path: string[] }>
}

async function proxyRequest(request: Request, context: RouteContext) {
  const { path } = await context.params
  const incoming = new URL(request.url)
  const target = new URL(path.join("/"), ensureTrailingSlash(AI_SERVICE_URL))
  target.search = incoming.search

  const headers = new Headers()
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value)
    }
  })

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
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
