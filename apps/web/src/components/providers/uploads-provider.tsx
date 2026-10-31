"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import { useSources } from "@/components/providers/sources-provider"
import {
  classifyDroppedFile,
  uploadDocumentFile,
  uploadInvoiceFile,
} from "@/lib/api/upload"

export type UploadStatus = "queued" | "uploading" | "processing" | "done" | "error"
export type UploadOrigin = "chat" | "sources"

export type UploadItem = {
  id: string
  file: File
  name: string
  kind: "document" | "invoice"
  status: UploadStatus
  /** 0 to 100 while the bytes are on the wire. */
  progress: number
  /** Result summary when done, reason when it failed. */
  detail?: string
  origin: UploadOrigin
  /** True once a chat message has taken this upload as its attachment. */
  attached: boolean
  previewUrl?: string
}

type UploadsContextValue = {
  items: UploadItem[]
  enqueue: (files: File[], origin: UploadOrigin) => void
  retry: (id: string) => void
  cancel: (id: string) => void
  dismiss: (id: string) => void
  markAttached: (ids: string[]) => void
}

const UploadsContext = createContext<UploadsContextValue | null>(null)

const ACCEPT_ERROR = "Solo se admiten PDF e imágenes (PNG, JPG, WEBP)."

export function UploadsProvider({ children }: { children: ReactNode }) {
  const { refresh } = useSources()
  const [items, setItems] = useState<UploadItem[]>([])
  const running = useRef(false)
  const controllers = useRef(new Map<string, AbortController>())

  const patch = useCallback((id: string, change: Partial<UploadItem>) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...change } : item)))
  }, [])

  const enqueue = useCallback((files: File[], origin: UploadOrigin) => {
    const next = files.map<UploadItem>((file) => {
      const kind = classifyDroppedFile(file)
      const base = {
        id: crypto.randomUUID(),
        file,
        name: file.name || "captura",
        origin,
        attached: false,
        progress: 0,
        previewUrl: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
      }
      if (kind === "unsupported") {
        return { ...base, kind: "document", status: "error", detail: ACCEPT_ERROR }
      }
      return { ...base, kind, status: "queued" }
    })
    setItems((current) => [...current, ...next])
  }, [])

  useEffect(() => {
    if (running.current) return
    const next = items.find((item) => item.status === "queued")
    if (!next) return
    running.current = true
    const controller = new AbortController()
    controllers.current.set(next.id, controller)
    patch(next.id, { status: "uploading", progress: 0 })
    const onProgress = (progress: number) =>
      patch(next.id, { progress, status: progress >= 100 ? "processing" : "uploading" })
    const task =
      next.kind === "invoice"
        ? uploadInvoiceFile(next.file, onProgress, controller.signal).then((result) =>
            result.ok
              ? { ok: true as const, detail: result.data.estado === "ok" ? "Factura extraída" : "Factura para revisar" }
              : result
          )
        : uploadDocumentFile(next.file, onProgress, controller.signal).then((result) =>
            result.ok
              ? { ok: true as const, detail: result.data.created ? `${result.data.n_chunks} fragmentos` : "Ya estaba indexado" }
              : result
          )
    void task.then(async (result) => {
      controllers.current.delete(next.id)
      if (result.ok) {
        patch(next.id, { status: "done", progress: 100, detail: result.detail })
        await refresh()
      } else {
        patch(next.id, { status: "error", detail: result.error.message })
      }
      running.current = false
      setItems((current) => [...current])
    })
  }, [items, patch, refresh])

  const retry = useCallback(
    (id: string) => patch(id, { status: "queued", progress: 0, detail: undefined }),
    [patch]
  )
  const cancel = useCallback((id: string) => controllers.current.get(id)?.abort(), [])
  const dismiss = useCallback((id: string) => {
    controllers.current.get(id)?.abort()
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])
  const markAttached = useCallback((ids: string[]) => {
    setItems((current) =>
      current.map((item) => (ids.includes(item.id) ? { ...item, attached: true } : item))
    )
  }, [])

  const value = useMemo(
    () => ({ items, enqueue, retry, cancel, dismiss, markAttached }),
    [items, enqueue, retry, cancel, dismiss, markAttached]
  )
  return <UploadsContext.Provider value={value}>{children}</UploadsContext.Provider>
}

export function useUploads() {
  const ctx = useContext(UploadsContext)
  if (!ctx) throw new Error("UploadsProvider missing")
  return ctx
}
