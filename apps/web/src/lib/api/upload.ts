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

export async function uploadInvoiceFile(
  file: File
): Promise<UploadResult<InvoiceUploadResponse>> {
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
  file: File
): Promise<UploadResult<DocumentUploadResponse>> {
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
