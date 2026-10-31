import { followIngestJob, type IngestStage } from "../api/ingest-events"
import { classifyDroppedFile, uploadDocumentFile, uploadInvoiceFile } from "../api/upload"
import { describeUploadError, UNSUPPORTED_MESSAGE } from "./errors"

export { CANCELLED_MESSAGE, UNSUPPORTED_MESSAGE } from "./errors"

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
  /** Step the service reports while it processes the file. */
  stage?: IngestStage
  /** Result summary when done, reason when it failed. */
  detail?: string
  /** The service already had this file: nothing was added. */
  duplicate?: boolean
  /** False when trying the same file again cannot work. */
  retryable: boolean
  /** The notification no longer lists it. */
  hidden?: boolean
  origin: UploadOrigin
  /** True once a chat message has taken this upload as its attachment. */
  attached: boolean
  previewUrl?: string
}


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
        retryable: true,
        previewUrl: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
      }
      if (kind === "unsupported") {
        return { ...base, kind: "document", status: "error", detail: UNSUPPORTED_MESSAGE, retryable: false }
      }
      return { ...base, kind, status: "queued" }
    })
    this.publish([...this.items, ...added])
    this.pump()
  }

  retry(id: string) {
    this.patch(id, { status: "queued", progress: 0, detail: undefined, stage: undefined, duplicate: undefined, hidden: false })
    this.pump()
  }

  /** Only possible while the bytes are still travelling: once the service has the file it finishes the job. */
  cancel(id: string) {
    const item = this.items.find((candidate) => candidate.id === id)
    if (item?.status === "queued") this.dismiss(id)
    else if (item?.status === "uploading") this.controllers.get(id)?.abort()
  }

  /** Hides the finished items from the notification; they keep their result in the sources list. */
  hideFinished() {
    this.publish(this.items.map((item) => (item.status === "done" || item.status === "error" ? { ...item, hidden: true } : item)))
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
    const jobId = crypto.randomUUID()
    const follow = new AbortController()
    const onProgress = (progress: number) =>
      this.patch(item.id, { progress, status: progress >= 100 ? "processing" : "uploading" })
    void followIngestJob(
      jobId,
      (event) => {
        const current = this.items.find((candidate) => candidate.id === item.id)
        if (current?.status === "uploading" || current?.status === "processing") {
          this.patch(item.id, { stage: event.stage, status: "processing", progress: 100 })
        }
      },
      follow.signal
    )
    try {
      const result =
        item.kind === "invoice"
          ? await uploadInvoiceFile(item.file, onProgress, signal, jobId).then((outcome) =>
              outcome.ok
                ? { ok: true as const, duplicate: false, detail: outcome.data.estado === "ok" ? "Factura extraída" : "Factura para revisar" }
                : outcome
            )
          : await uploadDocumentFile(item.file, onProgress, signal, jobId).then((outcome) =>
              outcome.ok
                ? {
                    ok: true as const,
                    duplicate: !outcome.data.created,
                    detail: outcome.data.created ? `${outcome.data.n_chunks} fragmentos indexados` : "Ya estaba indexado, no se añadió de nuevo",
                  }
                : outcome
            )
      if (result.ok) {
        this.patch(item.id, { status: "done", progress: 100, stage: "done", detail: result.detail, duplicate: result.duplicate })
        await this.onUploaded()
      } else {
        const { message, retryable } = describeUploadError(result.error)
        this.patch(item.id, { status: "error", stage: "error", detail: message, retryable })
      }
    } finally {
      follow.abort()
    }
  }
}
