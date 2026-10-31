export type SseFrame = { event: string; data: string }

/** Splits a byte stream into SSE frames. Handles CRLF, multi-line data and chunk boundaries inside a frame. */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<SseFrame> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n")
      let boundary = buffer.indexOf("\n\n")
      while (boundary !== -1) {
        const frame = parseFrame(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (frame) yield frame
        boundary = buffer.indexOf("\n\n")
      }
      if (done) break
    }
    const tail = parseFrame(buffer)
    if (tail) yield tail
  } finally {
    reader.releaseLock()
  }
}

function parseFrame(block: string): SseFrame | null {
  let event = "message"
  const data: string[] = []
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim()
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""))
  }
  return data.length > 0 ? { event, data: data.join("\n") } : null
}
