"use client"

import { createContext, useContext } from "react"

import type { Citation } from "@/lib/api/types"

export type CitationContextValue = {
  citations: readonly Citation[]
  activeIndex: number | null
  onOpen: (index: number) => void
}

export const CitationContext = createContext<CitationContextValue | null>(null)

export function useCitations(): CitationContextValue | null {
  return useContext(CitationContext)
}
