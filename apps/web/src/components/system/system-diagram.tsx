"use client"

import {
  ArrowDownIcon,
  ArrowRightIcon,
  DatabaseIcon,
  ListOrderedIcon,
  MonitorIcon,
  NetworkIcon,
  ScanTextIcon,
  SparklesIcon,
  VectorSquareIcon,
  WorkflowIcon,
  type LucideIcon,
} from "lucide-react"

import type { StepData } from "@/lib/chat/types"
import { duration } from "@/lib/format"
import {
  PIECES,
  STATUS_TEXT,
  UNKNOWN,
  litState,
  type Lit,
  type PieceId,
  type PieceStatus,
  type PieceUsage,
} from "@/lib/system/pieces"
import { cn } from "@/lib/utils"

const ICONS: Record<PieceId, LucideIcon> = {
  web: MonitorIcon,
  proxy: NetworkIcon,
  ai: WorkflowIcon,
  llm: SparklesIcon,
  embeddings: VectorSquareIcon,
  reranker: ListOrderedIcon,
  ocr: ScanTextIcon,
  sqlite: DatabaseIcon,
}

const DOT: Record<PieceStatus["status"], string> = {
  ok: "bg-[var(--ok-fg)]",
  degraded: "bg-[var(--review-fg)]",
  unavailable: "bg-destructive",
  unknown: "bg-muted-foreground/50",
}

const LIT: Record<Lit, string> = {
  working: "border-primary bg-primary/5 shadow-[0_0_0_3px_color-mix(in_oklch,var(--primary)_18%,transparent)]",
  carrier: "border-primary/40 bg-card",
  idle: "border-border bg-card",
}

function ms(value: number) {
  return `${value.toFixed(value < 10 ? 1 : 0).replace(".", ",")} ms`
}

type NodeProps = {
  id: PieceId
  status: PieceStatus
  step: StepData | null
  usage: PieceUsage | undefined
}

function Node({ id, status, step, usage }: NodeProps) {
  const piece = PIECES[id]
  const Icon = ICONS[id]
  const lit = litState(id, step)
  return (
    <li
      className={cn(
        "flex min-w-0 flex-col gap-1.5 rounded-lg border p-3 transition-[border-color,box-shadow,background-color] duration-200 ease-[var(--ease-out)]",
        LIT[lit]
      )}
      data-lit={lit}
      data-status={status.status}
      data-testid={`piece-${id}`}
    >
      <div className="flex items-center gap-2">
        <Icon aria-hidden className="size-4 shrink-0 text-muted-foreground" />
        <h3 className="truncate text-sm font-medium">{piece.label}</h3>
        {lit === "working" ? (
          <span className="ml-auto rounded-full bg-primary px-1.5 py-0.5 text-[0.6875rem] leading-none font-medium text-primary-foreground">
            En uso
          </span>
        ) : null}
      </div>
      <p className="truncate text-xs text-muted-foreground">{piece.role}</p>
      <div className="flex items-center gap-1.5 text-xs">
        <span aria-hidden className={cn("size-2 shrink-0 rounded-full", DOT[status.status])} />
        <span className="font-medium">{STATUS_TEXT[status.status]}</span>
        {status.latencyMs !== null ? (
          <span className="ml-auto tabular-nums text-muted-foreground" title="Latencia de la comprobación">
            {ms(status.latencyMs)}
          </span>
        ) : null}
      </div>
      {status.detail ? <p className="truncate font-mono text-[0.6875rem] text-muted-foreground">{status.detail}</p> : null}
      {usage ? (
        <p className="border-t border-border pt-1.5 text-xs text-muted-foreground" data-testid={`usage-${id}`}>
          Última consulta:{" "}
          <span className="tabular-nums text-foreground">{usage.seconds > 0 ? duration(usage.seconds) : "sin medir"}</span>
        </p>
      ) : null}
    </li>
  )
}

type SystemDiagramProps = {
  pieces: Record<PieceId, PieceStatus>
  step: StepData | null
  usage: Partial<Record<PieceId, PieceUsage>>
}

/** Top row: the path of a request. Bottom grid: what the service depends on. */
export function SystemDiagram({ pieces, step, usage }: SystemDiagramProps) {
  const node = (id: PieceId) => (
    <Node id={id} key={id} status={pieces[id] ?? UNKNOWN} step={step} usage={usage[id]} />
  )
  const path: PieceId[] = ["web", "proxy", "ai"]
  const dependencies: PieceId[] = ["llm", "embeddings", "reranker", "sqlite", "ocr"]
  return (
    <div className="flex flex-col gap-3" data-testid="system-diagram">
      <ol aria-label="Recorrido de una petición" className="grid grid-cols-1 items-stretch gap-2 sm:grid-cols-[1fr_auto_1fr_auto_1fr]">
        {path.flatMap((id, index) => [
          node(id),
          index < path.length - 1 ? (
            <li aria-hidden className="flex items-center justify-center text-muted-foreground" key={`${id}-arrow`}>
              <ArrowRightIcon className="hidden size-4 sm:block" />
              <ArrowDownIcon className="size-4 sm:hidden" />
            </li>
          ) : null,
        ])}
      </ol>
      <div aria-hidden className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        <span className="inline-flex items-center gap-1">
          <ArrowDownIcon className="size-3" />
          El servicio AI consulta
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>
      <ul aria-label="Dependencias del servicio" className="grid grid-cols-2 gap-2 xl:grid-cols-3">
        {dependencies.map(node)}
      </ul>
    </div>
  )
}
