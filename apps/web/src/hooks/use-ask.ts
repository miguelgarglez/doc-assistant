"use client"

import { useRef, useState } from "react"

import { api } from "@/lib/api/client"
import { toErrorBody } from "@/lib/api/errors"
import type { AskResponse, ErrorBody } from "@/lib/api/types"

export type AskStatus =
  | { kind: "idle" }
  | { kind: "loading"; question: string }
  | { kind: "success"; question: string; data: AskResponse }
  | { kind: "error"; question: string; error: ErrorBody }
  | { kind: "cancelled"; question: string }

export function useAsk() {
  const [status, setStatus] = useState<AskStatus>({ kind: "idle" })
  const abortRef = useRef<AbortController | null>(null)
  const generationRef = useRef(0)

  async function ask(question: string) {
    const trimmed = question.trim()
    if (!trimmed) {
      return
    }

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const generation = ++generationRef.current

    setStatus({ kind: "loading", question: trimmed })

    try {
      const { data, error } = await api.POST("/ask", {
        body: { question: trimmed },
        signal: controller.signal,
      })

      if (generation !== generationRef.current || controller.signal.aborted) {
        return
      }

      if (error) {
        setStatus({
          kind: "error",
          question: trimmed,
          error: toErrorBody(error),
        })
        return
      }

      if (!data) {
        setStatus({
          kind: "error",
          question: trimmed,
          error: {
            code: "empty_response",
            message: "El servicio no devolvió una respuesta.",
          },
        })
        return
      }

      setStatus({ kind: "success", question: trimmed, data })
    } catch (error) {
      if (generation !== generationRef.current || controller.signal.aborted) {
        return
      }
      if (
        (error instanceof DOMException && error.name === "AbortError") ||
        (error instanceof Error && error.name === "AbortError")
      ) {
        setStatus({ kind: "cancelled", question: trimmed })
        return
      }
      const message =
        error instanceof Error ? error.message : "Error desconocido"
      setStatus({
        kind: "error",
        question: trimmed,
        error: { code: "network_error", message },
      })
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
    }
  }

  function cancel() {
    generationRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    setStatus((current) => {
      if (current.kind !== "loading") {
        return current
      }
      return { kind: "cancelled", question: current.question }
    })
    return true
  }

  function reset() {
    generationRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    setStatus({ kind: "idle" })
  }

  return { status, ask, cancel, reset }
}
