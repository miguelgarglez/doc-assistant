import type { ErrorBody } from "@/lib/api/types"

export const UNSUPPORTED_MESSAGE = "Solo se admiten PDF e imágenes (PNG, JPG)."
export const CANCELLED_MESSAGE = "Subida cancelada."

/** What an upload failure means for the person, in Spanish. The API answers in English and generic. */
export function describeUploadError(error: ErrorBody): { message: string; retryable: boolean } {
  const detail = error.message.toLowerCase()
  switch (error.code) {
    case "cancelled":
      return { message: CANCELLED_MESSAGE, retryable: true }
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
      return { message: "No se pudo contactar con el servicio. Reintenta cuando vuelva la conexión.", retryable: true }
    case "timeout":
      return { message: "El servicio tardó demasiado en procesar el archivo.", retryable: true }
    case "adapter_error":
      return { message: "El modelo de lectura no respondió. Reintenta en unos segundos.", retryable: true }
    default:
      return { message: error.message || "No se pudo añadir el archivo.", retryable: true }
  }
}
