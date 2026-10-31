"use client"

import { createContext, useContext, useState, type ReactNode } from "react"

export type TraceStep = { id: string; status: "running" | "done"; label: string; elapsed_s?: number }
type TraceContextValue = { steps: TraceStep[]; clear: () => void; record: (step: TraceStep) => void }
const TraceContext = createContext<TraceContextValue | null>(null)

export function TraceProvider({ children }: { children: ReactNode }) {
  const [steps, setSteps] = useState<TraceStep[]>([])
  return <TraceContext.Provider value={{ steps, clear: () => setSteps([]), record: (step) => setSteps((old) => [...old, step]) }}>{children}</TraceContext.Provider>
}

export function useTrace() {
  const value = useContext(TraceContext)
  if (!value) throw new Error("TraceProvider missing")
  return value
}
