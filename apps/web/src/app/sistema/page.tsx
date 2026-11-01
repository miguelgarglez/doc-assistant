"use client"

import { RefreshCwIcon } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { useConversation } from "@/components/providers/chat-provider"
import { Page, PageHeader } from "@/components/shell/page"
import { HistoryStatusPanel } from "@/features/system"
import { SystemDiagram } from "@/features/system"
import { TracePanel } from "@/features/system"
import { Button } from "@/components/ui/button"
import { useHealth } from "@/features/system"
import { pieceUsage } from "@/features/system"

const REPLAY_STEP_MS = 700

// El guard de administrador se aplicará aquí cuando exista autenticación.
export default function SystemPage() {
  const health = useHealth()
  const { trace, busy } = useConversation()
  const [selected, setSelected] = useState<string | null>(null)
  const [replay, setReplay] = useState<number | null>(null)
  const steps = useMemo(() => trace?.steps ?? [], [trace])

  useEffect(() => {
    if (replay === null) return
    const timer = window.setTimeout(
      () => setReplay(replay >= steps.length - 1 ? null : replay + 1),
      replay >= steps.length - 1 ? REPLAY_STEP_MS * 1.5 : REPLAY_STEP_MS
    )
    return () => window.clearTimeout(timer)
  }, [replay, steps.length])

  const running = busy ? steps.findLast((step) => step.status === "running") : undefined
  const active =
    (replay !== null ? steps[replay] : undefined) ?? steps.find((step) => step.id === selected) ?? running ?? null
  const usage = useMemo(() => pieceUsage(steps), [steps])

  const checked = health.checkedAt
    ? new Date(health.checkedAt).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null

  return (
    <Page>
      <PageHeader
        actions={
          <>
            {checked ? (
              <span className="hidden text-xs text-muted-foreground sm:inline" data-testid="health-checked">
                Comprobado a las {checked}
              </span>
            ) : null}
            <Button disabled={health.checking} onClick={() => void health.refresh()} size="sm" type="button" variant="outline">
              <RefreshCwIcon className={health.checking ? "animate-spin" : undefined} data-icon="inline-start" />
              Comprobar
            </Button>
          </>
        }
        description="Qué piezas intervienen en una consulta, cómo están y dónde se fue el tiempo en la última."
        title="Sistema"
      />
      <div className="grid min-h-0 gap-5 lg:grid-cols-[minmax(0,1fr)_21rem]">
        <section aria-label="Piezas del sistema">
          <SystemDiagram pieces={health.pieces} step={active} usage={usage} />
        </section>
        <TracePanel
          activeId={active?.id ?? null}
          onReplay={() => setReplay(0)}
          onSelect={setSelected}
          replaying={replay !== null}
          trace={trace}
        />
      </div>
      <HistoryStatusPanel />
    </Page>
  )
}
