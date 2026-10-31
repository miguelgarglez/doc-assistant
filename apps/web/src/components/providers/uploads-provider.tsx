"use client"

import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react"

import { useSources } from "@/components/providers/sources-provider"
import { UploadStore, type UploadItem, type UploadOrigin } from "@/lib/uploads/store"

export type { UploadItem, UploadOrigin, UploadStatus } from "@/lib/uploads/store"

type UploadsContextValue = {
  items: UploadItem[]
  enqueue: (files: File[], origin: UploadOrigin) => void
  retry: (id: string) => void
  cancel: (id: string) => void
  dismiss: (id: string) => void
  markAttached: (ids: string[]) => void
  hideFinished: () => void
}

const UploadsContext = createContext<UploadsContextValue | null>(null)
const EMPTY: UploadItem[] = []

export function UploadsProvider({ children }: { children: ReactNode }) {
  const { refresh } = useSources()
  const [store] = useState(() => new UploadStore())
  useEffect(() => {
    store.setOnUploaded(refresh)
  }, [store, refresh])
  const items = useSyncExternalStore(store.subscribe, store.getSnapshot, () => EMPTY)

  const value = useMemo<UploadsContextValue>(
    () => ({
      items,
      enqueue: (files, origin) => store.enqueue(files, origin),
      retry: (id) => store.retry(id),
      cancel: (id) => store.cancel(id),
      dismiss: (id) => store.dismiss(id),
      markAttached: (ids) => store.markAttached(ids),
      hideFinished: () => store.hideFinished(),
    }),
    [items, store]
  )
  return <UploadsContext.Provider value={value}>{children}</UploadsContext.Provider>
}

export function useUploads() {
  const ctx = useContext(UploadsContext)
  if (!ctx) throw new Error("UploadsProvider missing")
  return ctx
}
