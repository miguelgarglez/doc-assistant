"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import type { ComponentsHealth } from "@/lib/api/types"
import { PIECES, UNKNOWN, type PieceId, type PieceStatus } from "@/lib/system/pieces"

type HealthState = {
  pieces: Record<PieceId, PieceStatus>
  checkedAt: number | null
  checking: boolean
}

const INTERVAL_MS = 8000

function empty(): Record<PieceId, PieceStatus> {
  return Object.fromEntries(Object.keys(PIECES).map((id) => [id, UNKNOWN])) as Record<PieceId, PieceStatus>
}

/**
 * Web and proxy are measured here: the page is loaded (web is up) and the round trip to the
 * proxy's cheapest route is the proxy latency. Everything behind it comes from `/health/components`.
 */
export function useHealth() {
  const [state, setState] = useState<HealthState>({ pieces: empty(), checkedAt: null, checking: true })
  const running = useRef(false)

  const check = useCallback(async () => {
    if (running.current) return
    running.current = true
    setState((current) => ({ ...current, checking: true }))
    const pieces = empty()
    pieces.web = { status: "ok", latencyMs: null, detail: "Esta página" }
    try {
      const started = performance.now()
      const ping = await fetch("/api/health", { cache: "no-store" })
      const latencyMs = Math.round((performance.now() - started) * 10) / 10
      pieces.proxy = { status: "ok", latencyMs, detail: "Ida y vuelta al servicio" }
      if (!ping.ok) {
        pieces.ai = { status: "unavailable", latencyMs: null, detail: `Responde ${ping.status}` }
      } else {
        const response = await fetch("/api/health/components", { cache: "no-store" })
        if (response.ok) {
          const body = (await response.json()) as ComponentsHealth
          for (const item of body.components) {
            pieces[item.id] = { status: item.status, latencyMs: item.latency_ms ?? null, detail: item.detail ?? null }
          }
        } else {
          pieces.ai = { status: "degraded", latencyMs: null, detail: "No expone el estado de las piezas" }
        }
      }
    } catch {
      pieces.proxy = { status: "unavailable", latencyMs: null, detail: "Sin respuesta del proxy" }
    }
    setState({ pieces, checkedAt: Date.now(), checking: false })
    running.current = false
  }, [])

  useEffect(() => {
    void check()
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void check()
    }, INTERVAL_MS)
    const onVisible = () => {
      if (document.visibilityState === "visible") void check()
    }
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [check])

  return { ...state, refresh: check }
}
