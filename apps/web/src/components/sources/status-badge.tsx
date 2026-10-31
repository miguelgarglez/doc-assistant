import type { Source } from "@/lib/api/types"
import { cn } from "@/lib/utils"

const STATUS: Record<Source["status"], { label: string; tone: string }> = {
  indexed: { label: "Indexada", tone: "bg-[var(--ok-bg)] text-[var(--ok-fg)]" },
  review: { label: "Revisar", tone: "bg-[var(--review-bg)] text-[var(--review-fg)]" },
  no_text: { label: "Sin texto", tone: "bg-[var(--review-bg)] text-[var(--review-fg)]" },
}

export function StatusBadge({ status }: { status: Source["status"] }) {
  const { label, tone } = STATUS[status]
  return (
    <span className={cn("inline-flex h-5 items-center rounded-full px-2 text-xs font-medium whitespace-nowrap", tone)}>
      {label}
    </span>
  )
}

export function KindLabel({ kind }: { kind: Source["kind"] }) {
  return <span className="text-xs text-muted-foreground">{kind === "pdf" ? "Documento" : "Factura"}</span>
}
