"use client"

import { createContext, useContext, useMemo, useState, type ReactNode } from "react"

import { AddSourcesDialog } from "@/features/uploads/add-sources-dialog"

type AddSourcesContextValue = {
  open: boolean
  setOpen: (open: boolean) => void
}

const AddSourcesContext = createContext<AddSourcesContextValue | null>(null)

/** Owns the "Añadir fuentes" dialog so the sidebar, the chat and the sources page can open the same one. */
export function AddSourcesProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const value = useMemo(() => ({ open, setOpen }), [open])
  return (
    <AddSourcesContext.Provider value={value}>
      {children}
      <AddSourcesDialog onOpenChange={setOpen} open={open} />
    </AddSourcesContext.Provider>
  )
}

export function useAddSources() {
  const ctx = useContext(AddSourcesContext)
  if (!ctx) throw new Error("AddSourcesProvider missing")
  return ctx
}
