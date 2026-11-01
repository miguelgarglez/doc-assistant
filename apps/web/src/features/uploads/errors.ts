import type { ErrorBody } from "@/lib/api/types"

export const UNSUPPORTED_MESSAGE = "Solo se admiten PDF e imágenes (PNG, JPG)."
export const CANCELLED_MESSAGE = "Subida cancelada."

/** What an upload failure means for the person, in Spanish. The API answers in English and generic. */
export function describeUploadError(error: ErrorBody): { message: string; retryable: boolean } {
  const detail = error.message.toLowerCase()
  if (error.reason === "size_limit" && error.limit != null) {
    return { message: `El archivo supera el límite de ${error.limit.toLocaleString("es-ES")} bytes. Reduce su tamaño y vuelve a subirlo.`, retryable: false }
  }
  if (error.reason === "page_limit" && error.limit != null) {
    return { message: `El PDF supera el límite de ${error.limit} páginas. Divídelo y sube las partes por separado.`, retryable: false }
  }
  if (error.reason === "pdf_protected") return { message: "El PDF está protegido. Retira la contraseña y vuelve a subirlo.", retryable: false }
  if (error.reason === "pdf_unreadable") return { message: "No se puede leer el PDF. Comprueba que no esté dañado y vuelve a guardarlo.", retryable: false }
  if (error.reason === "unsupported_type") return { message: UNSUPPORTED_MESSAGE, retryable: false }
  switch (error.code) {
    case "cancelled":
      return { message: CANCELLED_MESSAGE, retryable: false }
    case "upload_too_large":
      return {
        message: detail.includes("page") ? "El PDF tiene más páginas de las admitidas." : "El archivo supera el tamaño máximo admitido.",
        retryable: false,
      }
    case "invalid_file":
      return {
        message: detail.includes("empty") ? "El archivo está vacío." : "El archivo no es un PDF o una imagen válidos, o está dañado.",
        retryable: false,
      }
    case "network_error":
    case "upstream_unavailable":
      return { message: "No se pudo contactar con el servicio. Reintenta cuando vuelva la conexión.", retryable: true }
    case "timeout":
    case "model_timeout":
    case "queue_timeout":
      return { message: "El procesamiento tardó demasiado. Reintenta en unos minutos o divide el archivo.", retryable: true }
    case "model_busy":
    case "queue_full":
      return { message: "El servicio está ocupado. Reintenta en unos minutos.", retryable: true }
    case "adapter_error":
      return { message: "El modelo no pudo procesar el archivo. Revisa el servicio o divide el documento.", retryable: false }
    default:
      return { message: "No se pudo procesar el archivo por un error interno. Revisa el servicio.", retryable: false }
  }
}
