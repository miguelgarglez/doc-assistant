import { readUIMessageStream } from "ai"
import { expect, test } from "@playwright/test"

import { ChunkMapper, type AskChunk } from "../src/lib/chat/chunks"
import { readSse } from "../src/lib/chat/sse"
import type { AskMessage, StreamEvent } from "../src/lib/chat/types"
import { viewOfAssistant } from "../src/lib/chat/view"

const citation = {
  chunk_id: "c1",
  quote: "Alcance: 4 m.",
  doc: "sensor-demo",
  doc_id: "pdf-1",
  section: "2",
  pages: [1],
  fragment: "Alcance: 4 m. Temperatura de trabajo: 0 a 50 C.",
}

function ev(event: StreamEvent): StreamEvent {
  return event
}

const steps = (id: "retrieve" | "generate" | "verify", status: "running" | "done") =>
  ev({ event: "step", id, status, label: `${id} ${status}`, data: {}, elapsed_s: status === "done" ? 0.1 : null })

async function finalMessage(events: StreamEvent[], closed = true): Promise<AskMessage> {
  const mapper = new ChunkMapper()
  const chunks: AskChunk[] = [{ type: "start" }]
  for (const event of events) chunks.push(...mapper.push(event))
  if (!closed) chunks.push(...mapper.truncated())
  const stream = new ReadableStream<AskChunk>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  })
  let last: AskMessage | undefined
  for await (const message of readUIMessageStream<AskMessage>({ stream })) last = message
  if (!last) throw new Error("no message")
  return last
}

test.describe("transport: SSE a mensajes del AI SDK", () => {
  test("tokens provisionales y done: el texto final es done.answer", async () => {
    const message = await finalMessage([
      steps("retrieve", "running"),
      steps("retrieve", "done"),
      steps("generate", "running"),
      ev({ event: "token", text: "El alcance " }),
      ev({ event: "token", text: "es 4 m." }),
      steps("generate", "done"),
      steps("verify", "running"),
      steps("verify", "done"),
      ev({ event: "citations", citations: [citation] }),
      ev({
        event: "done", blocks_version: 1,
        ok: true,
        answer: "El alcance es 4 m.",
        citations: [citation],
        reason: "verified",
        suggestions: [],
        inline: "none",
        clarification: null,
        timings: { total: 2.5 },
      }),
    ])
    const view = viewOfAssistant(message, false)
    expect(view.kind).toBe("answer")
    if (view.kind !== "answer") return
    expect(view.text).toBe("El alcance es 4 m.")
    expect(view.citations).toEqual([citation])
    expect(view.result.timings.total).toBe(2.5)
    expect(view.steps.map((s) => `${s.id}:${s.status}`)).toEqual([
      "retrieve:done",
      "generate:done",
      "verify:done",
    ])
  })

  test("mientras llegan tokens la vista es provisional y no hay resultado", async () => {
    const message = await finalMessage(
      [steps("generate", "running"), ev({ event: "token", text: "Texto sin verificar" })],
      true
    )
    const view = viewOfAssistant(message, true)
    expect(view.kind).toBe("provisional")
    if (view.kind === "provisional") expect(view.text).toBe("Texto sin verificar")
  })

  test("refusal con retract elimina el texto provisional y conserva los pasos", async () => {
    const message = await finalMessage([
      steps("retrieve", "done"),
      steps("generate", "running"),
      ev({ event: "token", text: "Respuesta que no pasa la verificación" }),
      steps("generate", "done"),
      steps("verify", "running"),
      steps("verify", "done"),
      ev({
        event: "refusal",
        answer: "No dispongo de esa información en los documentos",
        reason: "verify:numbers",
        retract: true,
        suggestions: [{ doc: "sensor-demo", doc_id: "pdf-1", section: "2", heading: "Especificaciones", pages: [1] }],
      }),
      ev({
        event: "done", blocks_version: 1,
        ok: false,
        answer: "No dispongo de esa información en los documentos",
        citations: [],
        reason: "verify:numbers",
        suggestions: [],
        inline: "none",
        clarification: null,
        timings: { total: 1 },
      }),
    ])
    expect(message.parts.some((part) => part.type === "text")).toBe(false)
    const view = viewOfAssistant(message, false)
    expect(view.kind).toBe("refusal")
    if (view.kind !== "refusal") return
    expect(view.refusal.answer).toContain("No dispongo")
    expect(view.refusal.suggestions).toHaveLength(1)
    expect(view.steps.map((s) => s.id)).toEqual(["retrieve", "generate", "verify"])
  })

  test("un rechazo sin texto previo no necesita retirar nada", async () => {
    const message = await finalMessage([
      ev({ event: "refusal", answer: "No dispongo de esa información", reason: "llm_unanswerable", retract: false, suggestions: [] }),
      ev({ event: "done", blocks_version: 1, ok: false, answer: "No dispongo de esa información", citations: [], reason: "llm_unanswerable", suggestions: [], inline: "none", clarification: null, timings: {} }),
    ])
    expect(viewOfAssistant(message, false).kind).toBe("refusal")
  })

  test("una aclaración llega como evento propio y no como rechazo", async () => {
    const clarification = {
      prompt: "¿De qué factura?",
      detail: null,
      total: 1,
      candidates: [{ doc: "A-1", doc_id: "inv-a-1", emisor: null, cliente: null, fecha: null, total: null, question: "¿Qué datos tiene la factura A-1?" }],
    }
    const message = await finalMessage([
      steps("retrieve", "done"),
      ev({ event: "clarification", reason: "invoice:aclaracion", clarification }),
      ev({ event: "done", blocks_version: 1, ok: false, answer: "¿De qué factura?", citations: [], reason: "invoice:aclaracion", suggestions: [], inline: "none", clarification, timings: {} }),
    ])
    const view = viewOfAssistant(message, false)
    expect(view.kind).toBe("clarification")
    if (view.kind !== "clarification") return
    expect(view.clarification.clarification.candidates[0]?.question).toBe("¿Qué datos tiene la factura A-1?")
    expect(message.parts.filter((part) => part.type === "data-clarification")).toHaveLength(1)
    expect(message.parts.some((part) => part.type === "data-refusal")).toBe(false)
    expect(view.steps.map((s) => s.id)).toEqual(["retrieve"])
  })

  test("un done con aclaración, sin evento previo (servicio sin streaming), también es aclaración", async () => {
    const clarification = { prompt: "¿De qué factura?", detail: null, total: 0, candidates: [] }
    const message = await finalMessage([
      ev({ event: "done", blocks_version: 1, ok: false, answer: "¿De qué factura?", citations: [], reason: "invoice:aclaracion", suggestions: [], inline: "none", clarification, timings: {} }),
    ])
    expect(viewOfAssistant(message, false).kind).toBe("clarification")
  })

  test("un rechazo de factura sin candidatas sigue siendo rechazo", async () => {
    const message = await finalMessage([
      ev({ event: "refusal", answer: "No hay ninguna factura con número X-1.", reason: "invoice:factura_no_encontrada", retract: false, suggestions: [] }),
      ev({ event: "done", blocks_version: 1, ok: false, answer: "No hay ninguna factura con número X-1.", citations: [], reason: "invoice:factura_no_encontrada", suggestions: [], inline: "none", clarification: null, timings: {} }),
    ])
    expect(viewOfAssistant(message, false).kind).toBe("refusal")
  })

  test("error del servicio descarta los tokens y expone código y mensaje", async () => {
    const message = await finalMessage([
      ev({ event: "token", text: "parcial" }),
      ev({ event: "error", code: "adapter_error", message: "No responde el servidor." }),
    ])
    const view = viewOfAssistant(message, false)
    expect(view.kind).toBe("failed")
    if (view.kind === "failed") {
      expect(view.code).toBe("adapter_error")
      expect(view.message).toBe("No responde el servidor.")
    }
  })

  test("un stream cortado sin done es un error, no una respuesta", async () => {
    const message = await finalMessage([ev({ event: "token", text: "parcial" })], false)
    expect(viewOfAssistant(message, false).kind).toBe("failed")
  })

  test("sin resultado y sin generación en curso se muestra como detenida", async () => {
    const message = await finalMessage([ev({ event: "token", text: "parcial" })], true)
    expect(viewOfAssistant(message, false).kind).toBe("stopped")
  })
})

test.describe("lector SSE", () => {
  async function frames(chunks: string[]) {
    const encoder = new TextEncoder()
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
        controller.close()
      },
    })
    const out = []
    for await (const frame of readSse(body)) out.push(frame)
    return out
  }

  test("reconstruye tramas partidas entre trozos y con CRLF", async () => {
    const out = await frames(['event: token\r\ndata: {"te', 'xt":"hola"}\r\n\r\nevent: done\ndata: {"ok":true}\n\n'])
    expect(out).toEqual([
      { event: "token", data: '{"text":"hola"}' },
      { event: "done", blocks_version: 1, data: '{"ok":true}' },
    ])
  })

  test("ignora tramas sin datos y une datos de varias líneas", async () => {
    const out = await frames([": comentario\n\nevent: x\ndata: a\ndata: b\n\n"])
    expect(out).toEqual([{ event: "x", data: "a\nb" }])
  })
})
