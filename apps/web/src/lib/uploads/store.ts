import { classifyDroppedFile, uploadDocumentFile, uploadInvoiceFile } from "../api/upload"

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

export const UNSUPPORTED_MESSAGE = "Solo se admiten PDF e imágenes (PNG, JPG)."
export const CANCELLED_MESSAGE = "Subida cancelada."

/**
 * Upload queue outside React: one file at a time, state changes publish an immutable snapshot.
 */
export class UploadStore {
  private items: UploadItem[] = []
  private listeners = new Set<() => void>()
  private running = false
  private controllers = new Map<string, AbortController>()

  /** Set by the provider; fires after each success so the source list can refresh. */
  private onUploaded: () => void | Promise<void> = () => undefined

  setOnUploaded(callback: () => void | Promise<void>) {
    this.onUploaded = callback
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  getSnapshot = () => this.items

  enqueue(files: File[], origin: UploadOrigin) {
    const added = files.map<UploadItem>((file) => {
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
        return { ...base, kind: "document", status: "error", detail: UNSUPPORTED_MESSAGE }
      }
      return { ...base, kind, status: "queued" }
    })
    this.publish([...this.items, ...added])
    this.pump()
  }

  retry(id: string) {
    this.patch(id, { status: "queued", progress: 0, detail: undefined })
    this.pump()
  }

  cancel(id: string) {
    this.controllers.get(id)?.abort()
  }

  dismiss(id: string) {
    this.controllers.get(id)?.abort()
    this.publish(this.items.filter((item) => item.id !== id))
  }

  markAttached(ids: string[]) {
    this.publish(this.items.map((item) => (ids.includes(item.id) ? { ...item, attached: true } : item)))
  }

  private publish(next: UploadItem[]) {
    this.items = next
    for (const listener of this.listeners) listener()
  }

  private patch(id: string, change: Partial<UploadItem>) {
    this.publish(this.items.map((item) => (item.id === id ? { ...item, ...change } : item)))
  }

  private pump() {
    if (this.running) return
    const next = this.items.find((item) => item.status === "queued")
    if (!next) return
    this.running = true
    const controller = new AbortController()
    this.controllers.set(next.id, controller)
    this.patch(next.id, { status: "uploading", progress: 0 })
    void this.run(next, controller.signal).finally(() => {
      this.controllers.delete(next.id)
      this.running = false
      this.pump()
    })
  }

  private async run(item: UploadItem, signal: AbortSignal) {
    const onProgress = (progress: number) =>
      this.patch(item.id, { progress, status: progress >= 100 ? "processing" : "uploading" })
    const result =
      item.kind === "invoice"
        ? await uploadInvoiceFile(item.file, onProgress, signal).then((outcome) =>
            outcome.ok ? { ok: true as const, detail: outcome.data.estado === "ok" ? "Factura extraída" : "Factura para revisar" } : outcome
          )
        : await uploadDocumentFile(item.file, onProgress, signal).then((outcome) =>
            outcome.ok
              ? { ok: true as const, detail: outcome.data.created ? `${outcome.data.n_chunks} fragmentos` : "Ya estaba indexado" }
              : outcome
          )
    if (result.ok) {
      this.patch(item.id, { status: "done", progress: 100, detail: result.detail })
      await this.onUploaded()
    } else {
      this.patch(item.id, { status: "error", detail: result.error.message })
    }
  }
}
