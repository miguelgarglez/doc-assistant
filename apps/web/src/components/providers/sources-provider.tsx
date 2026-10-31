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
  reindex: (id: string) => Promise<ErrorBody | null>
}

const SourcesContext = createContext<SourcesContextValue | null>(null)

async function failure(response: Response): Promise<ErrorBody> {
  const body: unknown = await response.json().catch(() => null)
  return toErrorBody(body ?? { code: "request_failed", message: `La operación falló (${response.status}).` })
}

/** One shared catalogue: chat, sources and system read the same list, and uploads refresh it. */
export function SourcesProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SourcesState>({ status: "loading", items: [] })

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/sources", { cache: "no-store" })
      if (!response.ok) throw await failure(response)
      const items = (await response.json()) as Source[]
      setState({ status: "ready", items })
    } catch (error) {
      const body =
        error && typeof error === "object" && "code" in error
          ? (error as ErrorBody)
          : { code: "network_error", message: "No se pudo contactar con el servicio." }
      setState((current) => ({ status: "error", items: current.items, error: body }))
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const mutate = useCallback(
    async (url: string, method: "DELETE" | "POST") => {
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
      reindex: (id) => mutate(`/api/sources/${encodeURIComponent(id)}/reindex`, "POST"),
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
