"use client"

import { useState } from "react"

import { api } from "@/lib/api/client"
import { toErrorBody } from "@/lib/api/errors"
import type { AskResponse, ErrorBody } from "@/lib/api/types"

export type AskStatus =
  | { kind: "idle" }
  | { kind: "loading"; question: string }
  | { kind: "success"; question: string; data: AskResponse }
  | { kind: "error"; question: string; error: ErrorBody }

export function useAsk() {
  const [status, setStatus] = useState<AskStatus>({ kind: "idle" })

  async function ask(question: string) {
    const trimmed = question.trim()
    if (!trimmed) {
      return
    }

    setStatus({ kind: "loading", question: trimmed })

    const { data, error } = await api.POST("/ask", {
      body: { question: trimmed },
    })

    if (error) {
      setStatus({ kind: "error", question: trimmed, error: toErrorBody(error) })
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
  }

  function reset() {
    setStatus({ kind: "idle" })
  }

  return { status, ask, reset }
}
