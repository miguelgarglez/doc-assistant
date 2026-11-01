import type { ChatTransport } from "ai"

import { ChunkMapper, type AskChunk } from "./chunks"
import { readSse } from "./sse"
import type { AskMessage, DoneEvent, StreamEvent } from "./types"
import { lastQuestion } from "./view"

const STREAM_TIMEOUT_MS = 180_000

/** Streams `/ask/stream` through the SDK transport contract, so `useChat` owns state, abort and regenerate. */
export class AskTransport implements ChatTransport<AskMessage> {
  constructor(private readonly base = "/api") {}

  async sendMessages({
    messages,
    abortSignal,
  }: Parameters<ChatTransport<AskMessage>["sendMessages"]>[0]): Promise<ReadableStream<AskChunk>> {
    const question = lastQuestion(messages)?.trim() ?? ""
    const controller = new AbortController()
    const signal = AbortSignal.any([
      controller.signal,
      AbortSignal.timeout(STREAM_TIMEOUT_MS),
      ...(abortSignal ? [abortSignal] : []),
    ])
    const base = this.base

    return new ReadableStream<AskChunk>({
      async start(out) {
        out.enqueue({ type: "start" })
        const mapper = new ChunkMapper()
        const emit = (events: StreamEvent[]) => {
          for (const event of events) for (const chunk of mapper.push(event)) out.enqueue(chunk)
        }
        try {
          if (!question) {
            emit([{ event: "error", code: "empty_question", message: "Escribe una pregunta." }])
            return
          }
          const response = await fetch(`${base}/ask/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
            body: JSON.stringify({ question }),
            signal,
          })
          if (response.status === 404 || response.status === 405) {
            emit(await askWithoutStreaming(base, question, signal))
            return
          }
          if (!response.ok || !response.body) {
            emit([await failureFrom(response)])
            return
          }
          for await (const frame of readSse(response.body)) {
            const event = parseEvent(frame.event, frame.data)
            if (event) emit([event])
          }
          for (const chunk of mapper.truncated()) out.enqueue(chunk)
        } catch (error) {
          if (signal.aborted && !isTimeout(signal)) return
          const message = isTimeout(signal)
            ? "El servicio tardó demasiado en responder."
            : error instanceof Error
              ? error.message
              : "Error desconocido"
          emit([{ event: "error", code: isTimeout(signal) ? "timeout" : "network_error", message }])
        } finally {
          try {
            out.close()
          } catch {
            // already closed by cancel()
          }
        }
      },
      cancel() {
        controller.abort()
      },
    })
  }

  async reconnectToStream(): Promise<null> {
    return null
  }
}

function isTimeout(signal: AbortSignal): boolean {
  return signal.aborted && signal.reason instanceof DOMException && signal.reason.name === "TimeoutError"
}

function parseEvent(name: string, data: string): StreamEvent | null {
  try {
    return { event: name, ...JSON.parse(data) } as StreamEvent
  } catch {
    return null
  }
}

async function failureFrom(response: Response): Promise<StreamEvent> {
  const body = (await response.json().catch(() => null)) as { code?: string; message?: string } | null
  if (response.status === 422) {
    return { event: "error", code: "invalid_question", message: "La pregunta no es válida (1 a 1000 caracteres)." }
  }
  return {
    event: "error",
    code: body?.code ?? "request_failed",
    message: body?.message ?? `No se pudo iniciar la consulta (${response.status}).`,
  }
}

/** Services without `/ask/stream` still answer `/ask`: the result is replayed as one `done` event. */
async function askWithoutStreaming(base: string, question: string, signal: AbortSignal): Promise<StreamEvent[]> {
  const response = await fetch(`${base}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  })
  if (!response.ok) return [await failureFrom(response)]
  const data = (await response.json()) as Omit<DoneEvent, "event" | "timings" | "request_id"> & { timings?: Record<string, number> }
  return [{ event: "done", timings: {}, suggestions: [], ...data, request_id: response.headers.get("x-request-id") ?? "" }]
}
