import type { IngestStage } from "../api/ingest-events"
import type { UploadItem } from "./store"

const STAGE_TEXT: Partial<Record<IngestStage, string>> = {
  received: "Recibido",
  reading: "Leyendo el PDF…",
  ocr: "Reconociendo el texto (OCR)…",
  extracting: "Extrayendo los campos…",
  indexing: "Indexando…",
}

/** One line for a file, in the order the file goes through: queue, bytes, the service's own steps, result. */
export function uploadStatusText(item: UploadItem): string {
  switch (item.status) {
    case "queued":
      return "En cola"
    case "uploading":
      return `Subiendo ${item.progress}%`
    case "processing":
      return (item.stage && STAGE_TEXT[item.stage]) || "Procesando…"
    case "done":
      return item.detail ?? "Listo"
    case "error":
      return item.detail ?? "Error"
  }
}

export type UploadSummary = {
  total: number
  active: number
  done: number
  failed: number
  title: string
}

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`

export function summarizeUploads(items: readonly UploadItem[]): UploadSummary {
  const total = items.length
  const failed = items.filter((item) => item.status === "error").length
  const done = items.filter((item) => item.status === "done").length
  const active = total - failed - done
  let title: string
  if (active > 0) title = total === 1 ? "Añadiendo una fuente" : `Añadiendo fuentes: ${done + failed} de ${total}`
  else if (failed === 0) title = done === 1 ? "Fuente añadida" : `${plural(done, "fuente añadida", "fuentes añadidas")}`
  else if (done === 0) title = failed === 1 ? "No se pudo añadir" : `No se pudieron añadir ${failed} archivos`
  else title = `${plural(done, "añadida", "añadidas")}, ${plural(failed, "con error", "con error")}`
  return { total, active, done, failed, title }
}

/** The files that are not finished can still change: the notification must not disappear under them. */
export function isActive(item: UploadItem): boolean {
  return item.status === "queued" || item.status === "uploading" || item.status === "processing"
}
