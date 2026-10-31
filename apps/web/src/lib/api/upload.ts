import { api } from "@/lib/api/client"
import { toErrorBody } from "@/lib/api/errors"
import type {
  DocumentUploadResponse,
  ErrorBody,
  InvoiceUploadResponse,
} from "@/lib/api/types"

type UploadResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ErrorBody }

type ProgressHandler = (progress: number) => void

function multipartFile(file: File) {
  return {
    body: { file: file as unknown as string },
    bodySerializer() {
      const form = new FormData()
      form.append("file", file)
      return form
    },
  }
}

async function uploadWithProgress<T>(
  path: string,
  file: File,
  onProgress?: ProgressHandler,
  signal?: AbortSignal,
  jobId?: string
): Promise<UploadResult<T>> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", `/api${path}${jobId ? `?job=${encodeURIComponent(jobId)}` : ""}`)
    xhr.responseType = "json"
    xhr.timeout = 180_000

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress?.(Math.round((event.loaded / event.total) * 100))
    }

    const abort = () => xhr.abort()
    signal?.addEventListener("abort", abort, { once: true })

    xhr.onload = () => {
      signal?.removeEventListener("abort", abort)
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100)
        resolve({ ok: true, data: xhr.response as T })
        return
      }
      const body = xhr.response as Partial<ErrorBody> | null
      resolve({
        ok: false,
        error: toErrorBody(
          body ?? {
            code: "upload_failed",
            message: `La subida falló (${xhr.status}).`,
          }
        ),
      })
    }

    xhr.onerror = () => {
      signal?.removeEventListener("abort", abort)
      resolve({
        ok: false,
        error: {
          code: "network_error",
          message: "No se pudo contactar con el servicio.",
        },
      })
    }

    xhr.ontimeout = () => {
      signal?.removeEventListener("abort", abort)
      resolve({ ok: false, error: { code: "timeout", message: "La subida ha agotado el tiempo de espera." } })
    }

    xhr.onabort = () => {
      signal?.removeEventListener("abort", abort)
      resolve({
        ok: false,
        error: {
          code: "cancelled",
          message: "Subida cancelada.",
        },
      })
    }

    const form = new FormData()
    form.append("file", file)
    if (signal?.aborted) {
      resolve({ ok: false, error: { code: "cancelled", message: "Subida cancelada." } })
    } else {
      xhr.send(form)
    }
  })
}

export async function uploadInvoiceFile(
  file: File,
  onProgress?: ProgressHandler,
  signal?: AbortSignal,
  jobId?: string
): Promise<UploadResult<InvoiceUploadResponse>> {
  if (onProgress || signal) {
    return uploadWithProgress<InvoiceUploadResponse>(
      "/invoices/upload",
      file,
      onProgress,
      signal,
      jobId
    )
  }
  const { data, error } = await api.POST("/invoices/upload", multipartFile(file))

  if (error) {
    return { ok: false, error: toErrorBody(error) }
  }
  if (!data) {
    return {
      ok: false,
      error: {
        code: "empty_response",
        message: "El servicio no devolvió una respuesta.",
      },
    }
  }
  return { ok: true, data }
}

export async function uploadDocumentFile(
  file: File,
  onProgress?: ProgressHandler,
  signal?: AbortSignal,
  jobId?: string
): Promise<UploadResult<DocumentUploadResponse>> {
  if (onProgress || signal) {
    return uploadWithProgress<DocumentUploadResponse>(
      "/documents",
      file,
      onProgress,
      signal,
      jobId
    )
  }
  const { data, error } = await api.POST("/documents", multipartFile(file))

  if (error) {
    return { ok: false, error: toErrorBody(error) }
  }
  if (!data) {
    return {
      ok: false,
      error: {
        code: "empty_response",
        message: "El servicio no devolvió una respuesta.",
      },
    }
  }
  return { ok: true, data }
}

export function classifyDroppedFile(
  file: File
): "document" | "invoice" | "unsupported" {
  const type = file.type
  const name = file.name.toLowerCase()
  if (type === "application/pdf" || name.endsWith(".pdf")) {
    return "document"
  }
  if (type === "image/png" || type === "image/jpeg" || /\.(png|jpe?g)$/i.test(name)) {
    return "invoice"
  }
  return "unsupported"
}
