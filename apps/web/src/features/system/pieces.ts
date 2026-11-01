import type { ComponentHealth } from "@/lib/api/types"
import type { StepData, StepId } from "@/features/chat"

export type PieceId = "web" | "proxy" | ComponentHealth["id"]

export type PieceInfo = { id: PieceId; label: string; role: string }

export const PIECES: Record<PieceId, PieceInfo> = {
  web: { id: "web", label: "Navegador", role: "Interfaz de esta página" },
  proxy: { id: "proxy", label: "Proxy", role: "Reenvía las peticiones" },
  ai: { id: "ai", label: "Servicio AI", role: "Orquesta la consulta" },
  llm: { id: "llm", label: "LLM", role: "Redacta la respuesta" },
  embeddings: { id: "embeddings", label: "Embeddings", role: "Vectoriza texto" },
  reranker: { id: "reranker", label: "Reranker", role: "Ordena fragmentos" },
  ocr: { id: "ocr", label: "OCR", role: "Lee facturas en imagen" },
  sqlite: { id: "sqlite", label: "Índice", role: "Fragmentos y facturas" },
}

/** The piece that does the work in each pipeline step. The service orchestrates the ones with no model. */
export const STEP_PIECES: Record<StepId, readonly PieceId[]> = {
  route: ["ai"],
  meta: ["ai", "sqlite"],
  invoices: ["ai", "sqlite"],
  retrieve: ["embeddings", "sqlite"],
  rerank: ["reranker"],
  generate: ["llm"],
  verify: ["ai"],
}

/** Every request crosses these; they are lit as "carrying" while any step runs. */
export const CARRIERS: readonly PieceId[] = ["web", "proxy", "ai"]

export type Lit = "working" | "carrier" | "idle"

export function litState(piece: PieceId, step: StepData | null): Lit {
  if (!step) return "idle"
  if (STEP_PIECES[step.id].includes(piece)) return "working"
  return CARRIERS.includes(piece) ? "carrier" : "idle"
}

export type PieceUsage = { seconds: number; steps: number }

/** Time each piece spent in the last request, summed over the steps it worked in. */
export function pieceUsage(steps: readonly StepData[]): Partial<Record<PieceId, PieceUsage>> {
  const usage: Partial<Record<PieceId, PieceUsage>> = {}
  for (const step of steps) {
    for (const piece of STEP_PIECES[step.id]) {
      const current = usage[piece] ?? { seconds: 0, steps: 0 }
      usage[piece] = { seconds: current.seconds + (step.elapsed_s ?? 0), steps: current.steps + 1 }
    }
  }
  return usage
}

export type PieceStatus = {
  status: ComponentHealth["status"] | "unknown"
  latencyMs: number | null
  detail: string | null
}

export const UNKNOWN: PieceStatus = { status: "unknown", latencyMs: null, detail: null }

export const STATUS_TEXT: Record<PieceStatus["status"], string> = {
  ok: "Operativo",
  degraded: "Cargando o lento",
  unavailable: "No disponible",
  unknown: "Sin medir",
}
