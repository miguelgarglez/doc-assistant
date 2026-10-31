"use client"

import { useRef, useState } from "react"
import { api } from "@/lib/api/client"
import { toErrorBody } from "@/lib/api/errors"
import { useTrace, type TraceStep } from "@/components/system/trace-provider"
import type { AskResponse, ErrorBody } from "@/lib/api/types"

export type AskStatus =
  | { kind: "idle" }
  | { kind: "loading"; question: string; text: string }
  | { kind: "success"; question: string; data: AskResponse }
  | { kind: "error"; question: string; error: ErrorBody }
  | { kind: "cancelled"; question: string }

export function useAsk() {
  const [status, setStatus] = useState<AskStatus>({ kind: "idle" })
  const abortRef = useRef<AbortController | null>(null)
  const generationRef = useRef(0)
  const trace = useTrace()

  async function ask(question: string) {
    const trimmed = question.trim()
    if (!trimmed) return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const generation = ++generationRef.current
    trace.clear()
    setStatus({ kind: "loading", question: trimmed, text: "" })
    try {
      const response = await fetch("/api/ask/stream", { method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify({ question: trimmed }), signal: AbortSignal.any([controller.signal, AbortSignal.timeout(180_000)]) })
      if ([404, 405, 502].includes(response.status)) {
        const { data, error } = await api.POST("/ask", { body: { question: trimmed }, signal: controller.signal })
        if (generation !== generationRef.current || controller.signal.aborted) return
        if (error || !data) setStatus({ kind: "error", question: trimmed, error: error ? toErrorBody(error) : { code: "empty_response", message: "El servicio no devolvió una respuesta." } })
        else setStatus({ kind: "success", question: trimmed, data })
        return
      }
      if (!response.ok || !response.body || !response.headers.get("content-type")?.includes("text/event-stream")) throw new Error("No se pudo iniciar la consulta.")
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let terminal = false
      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n")
        let boundary: number
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          const block = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const event = block.split("\n").find((line) => line.startsWith("event:"))?.slice(6).trim()
          const payload = block.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n")
          if (!event || !payload) continue
          const data = JSON.parse(payload)
          if (generation !== generationRef.current || controller.signal.aborted) return
          if (event === "step") trace.record(data as TraceStep)
          if (event === "token") setStatus((current) => current.kind === "loading" ? { ...current, text: current.text + String(data.text) } : current)
          if (event === "refusal" && data.retract) setStatus((current) => current.kind === "loading" ? { ...current, text: "" } : current)
          if (event === "done") { terminal = true; setStatus({ kind: "success", question: trimmed, data: data as AskResponse }) }
          if (event === "error") { terminal = true; setStatus({ kind: "error", question: trimmed, error: { code: String(data.code), message: String(data.message) } }) }
        }
        if (done) break
      }
      if (!terminal) throw new Error("La respuesta terminó antes de completarse.")
    } catch (error) {
      if (generation !== generationRef.current || controller.signal.aborted) return
      setStatus({ kind: "error", question: trimmed, error: { code: "network_error", message: error instanceof Error ? error.message : "Error desconocido" } })
    } finally {
      if (abortRef.current === controller) abortRef.current = null
    }
  }
  function cancel() {
    generationRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    setStatus((current) => current.kind === "loading" ? { kind: "cancelled", question: current.question } : current)
    return true
  }
  return { status, ask, cancel }
}
