import { expect, test } from "@playwright/test"

test("proxy permite solo origen local y añade el token en servidor", async () => {
  const previousFetch = globalThis.fetch
  const previousToken = process.env.DOC_ASSISTANT_HISTORY_TOKEN
  process.env.DOC_ASSISTANT_HISTORY_TOKEN = "synthetic-token"
  const forwarded: Headers[] = []
  globalThis.fetch = async (_input, init) => {
    forwarded.push(new Headers(init?.headers))
    return new Response("{}", { status: 200 })
  }
  try {
    const route = await import("../src/app/api/[...path]/route")
    const call = (host: string, origin?: string, extra: Record<string, string> = {}) => route.POST(
      new Request("http://localhost:3300/api/history/feedback", {
        method: "POST", headers: { host, ...(origin ? { origin } : {}), ...extra }, body: "{}",
      }),
      { params: Promise.resolve({ path: ["history", "feedback"] }) },
    )
    expect((await call("127.0.0.1:3300", "http://127.0.0.1:3300")).status).toBe(200)
    expect(forwarded[0].get("x-history-token")).toBe("synthetic-token")
    expect((await call("localhost:3300", "http://localhost:3300")).status).toBe(200)
    expect((await call("127.0.0.1:3300", "http://evil.example")).status).toBe(403)
    expect((await call("evil.example:3300", "http://evil.example:3300")).status).toBe(403)
    expect((await call("127.0.0.1:3300")).status).toBe(403)
    expect((await call("127.0.0.1:3300", "http://127.0.0.1:3300", { "sec-fetch-site": "cross-site" })).status).toBe(403)
    expect(forwarded).toHaveLength(2)
  } finally {
    globalThis.fetch = previousFetch
    if (previousToken === undefined) delete process.env.DOC_ASSISTANT_HISTORY_TOKEN
    else process.env.DOC_ASSISTANT_HISTORY_TOKEN = previousToken
  }
})
