"use client"

import { useCallback, useEffect, useState } from "react"

const STORAGE_KEY = "doc-assistant.question-history"
const MAX = 40

function readStored(): string[] {
  if (typeof window === "undefined") {
    return []
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item): item is string => typeof item === "string")
  } catch {
    return []
  }
}

export function useQuestionHistory() {
  const [items, setItems] = useState<string[]>(() => readStored())
  const [cursor, setCursor] = useState<number | null>(null)

  useEffect(() => {
    try { window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items)) } catch { /* El historial sigue disponible en memoria. */ }
  }, [items])

  const push = useCallback((question: string) => {
    const trimmed = question.trim()
    if (!trimmed) return
    setItems((current) => {
      const next = [
        trimmed,
        ...current.filter((item) => item !== trimmed),
      ].slice(0, MAX)
      return next
    })
    setCursor(null)
  }, [])

  const peek = useCallback(
    (direction: "up" | "down"): string | null => {
      if (items.length === 0) return null
      if (direction === "up") {
        const next =
          cursor === null ? 0 : Math.min(cursor + 1, items.length - 1)
        setCursor(next)
        return items[next] ?? null
      }
      if (cursor === null) return null
      if (cursor <= 0) {
        setCursor(null)
        return ""
      }
      const next = cursor - 1
      setCursor(next)
      return items[next] ?? null
    },
    [cursor, items]
  )

  return { items, push, peek, cursor }
}
