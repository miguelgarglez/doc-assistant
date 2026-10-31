"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

import { toErrorBody } from "@/lib/api/errors"
import type { ErrorBody, Source } from "@/lib/api/types"

type SourcesState =
  | { status: "loading"; items: Source[] }
  | { status: "ready"; items: Source[] }
  | { status: "error"; items: Source[]; error: ErrorBody }

type SourcesContextValue = SourcesState & {
  refresh: () => Promise<void>
  remove: (id: string) => Promise<ErrorBody | null>
}

const SourcesContext = createContext<SourcesContextValue | null>(null)

async function failure(response: Response): Promise<ErrorBody> {
  const body: unknown = await response.json().catch(() => null)
  return toErrorBody(body ?? { code: "request_failed", message: `La operación falló (${response.status}).` })
}

async function load(): Promise<SourcesState | { status: "error"; error: ErrorBody }> {
  try {
    const response = await fetch("/api/sources", { cache: "no-store" })
    if (!response.ok) throw await failure(response)
    return { status: "ready", items: (await response.json()) as Source[] }
  } catch (error) {
    const body =
      error && typeof error === "object" && "code" in error
        ? (error as ErrorBody)
        : { code: "network_error", message: "No se pudo contactar con el servicio." }
    return { status: "error", error: body }
  }
}

/** One shared catalogue: chat, sources and system read the same list, and uploads refresh it. */
export function SourcesProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SourcesState>({ status: "loading", items: [] })

  const apply = useCallback((next: Awaited<ReturnType<typeof load>>) => {
    setState((current) =>
      next.status === "error" ? { status: "error", items: current.items, error: next.error } : (next as SourcesState)
    )
  }, [])
  const refresh = useCallback(async () => apply(await load()), [apply])

  useEffect(() => {
    let cancelled = false
    void load().then((next) => {
      if (!cancelled) apply(next)
    })
    return () => {
      cancelled = true
    }
  }, [apply])

  const mutate = useCallback(
    async (url: string, method: "DELETE") => {
      try {
        const response = await fetch(url, { method })
        if (!response.ok) return await failure(response)
        await refresh()
        return null
      } catch {
        return { code: "network_error", message: "No se pudo contactar con el servicio." }
      }
    },
    [refresh]
  )

  const value = useMemo<SourcesContextValue>(
    () => ({
      ...state,
      refresh,
      remove: (id) => mutate(`/api/sources/${encodeURIComponent(id)}`, "DELETE"),
    }),
    [state, refresh, mutate]
  )
  return <SourcesContext.Provider value={value}>{children}</SourcesContext.Provider>
}

export function useSources() {
  const ctx = useContext(SourcesContext)
  if (!ctx) throw new Error("SourcesProvider missing")
  return ctx
}
