"use client"

import { PlayIcon } from "lucide-react"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import type { Trace } from "@/features/chat"
import { duration } from "@/lib/format"
import { PIECES, STEP_PIECES } from "@/features/system/pieces"
import { cn } from "@/lib/utils"

type TracePanelProps = {
  trace: Trace | null
  activeId: string | null
  replaying: boolean
  onSelect: (id: string | null) => void
  onReplay: () => void
}

export function TracePanel({ trace, activeId, replaying, onSelect, onReplay }: TracePanelProps) {
  const longest = Math.max(0.001, ...(trace?.steps.map((step) => step.elapsed_s ?? 0) ?? []))
  return (
    <section aria-labelledby="trace-heading" className="flex min-h-0 flex-col rounded-xl border border-border bg-card" data-testid="trace-panel">
      <header className="flex items-start justify-between gap-3 border-b border-border p-3">
        <div className="min-w-0">
          <h2 className="font-heading text-sm font-semibold" id="trace-heading">
            Última consulta
          </h2>
          {trace ? (
            <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground" data-testid="trace-question">
              {trace.question ? `«${trace.question}»` : "Sin texto"}
              {trace.total === null ? "" : ` · ${duration(trace.total)} en total`}
            </p>
          ) : null}
          {trace?.code ? (
            <p className="mt-0.5 font-mono text-xs text-muted-foreground" data-testid="trace-code">
              {trace.code}
            </p>
          ) : null}
        </div>
        <Button data-testid="replay-trace" disabled={!trace?.steps.length || replaying} onClick={onReplay} size="sm" type="button" variant="outline">
          <PlayIcon data-icon="inline-start" />
          Reproducir
        </Button>
      </header>
      {trace ? (
        <ol className="flex min-h-0 flex-1 flex-col overflow-y-auto p-1.5">
          {trace.steps.map((step) => {
            const active = activeId === step.id
            return (
              <li key={step.id}>
                <button
                  aria-pressed={active}
                  className={cn(
                    "flex w-full cursor-pointer flex-col gap-1 rounded-md px-2.5 py-2 text-left transition-colors duration-150 outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50",
                    active && "bg-muted"
                  )}
                  data-testid={`trace-step-${step.id}`}
                  onBlur={() => onSelect(null)}
                  onClick={() => onSelect(step.id)}
                  onMouseEnter={() => onSelect(step.id)}
                  onMouseLeave={() => onSelect(null)}
                  type="button"
                >
                  <span className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate">{step.label}</span>
                    <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                      {step.elapsed_s === null ? (step.status === "running" ? "en curso" : "—") : duration(step.elapsed_s)}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-1 flex-1 overflow-hidden rounded-full bg-secondary">
                      <span
                        className="block h-full rounded-full bg-primary/70"
                        style={{ width: `${Math.max(2, ((step.elapsed_s ?? 0) / longest) * 100)}%` }}
                      />
                    </span>
                    <span className="shrink-0 text-[0.6875rem] text-muted-foreground">
                      {STEP_PIECES[step.id].map((piece) => PIECES[piece].label).join(" + ")}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      ) : (
        <div className="flex flex-col items-start gap-2 p-4 text-sm text-muted-foreground" data-testid="trace-empty">
          <p>Todavía no hay ninguna consulta en esta sesión.</p>
          <Link className="font-medium text-foreground underline underline-offset-4" href="/">
            Haz una pregunta en el chat
          </Link>
          <p className="text-xs">Aquí verás qué piezas trabajaron y cuánto tardó cada paso.</p>
        </div>
      )}
    </section>
  )
}
