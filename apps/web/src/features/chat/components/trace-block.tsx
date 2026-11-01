"use client"

import {
  BookOpenCheckIcon,
  FileSearchIcon,
  ListOrderedIcon,
  ReceiptTextIcon,
  RouteIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TableIcon,
  type LucideIcon,
} from "lucide-react"

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought"
import { Shimmer } from "@/components/ai-elements/shimmer"
import type { StepData, StepId } from "@/features/chat/lib/types"
import { duration } from "@/lib/format"

const ICONS: Record<StepId, LucideIcon> = {
  route: RouteIcon,
  meta: TableIcon,
  invoices: ReceiptTextIcon,
  retrieve: FileSearchIcon,
  rerank: ListOrderedIcon,
  generate: SparklesIcon,
  verify: ShieldCheckIcon,
}

type TraceBlockProps = {
  steps: StepData[]
  live: boolean
  total: number | null
}

/** Collapsed by default: one line while working, "N pasos · X s" afterwards, full list on demand. */
export function TraceBlock({ steps, live, total }: TraceBlockProps) {
  if (steps.length === 0) return null
  const current = steps.findLast((step) => step.status === "running") ?? steps.at(-1)
  return (
    <ChainOfThought data-testid="trace">
      <ChainOfThoughtHeader>
        {live && current ? (
          <Shimmer>{current.label}</Shimmer>
        ) : (
          <span className="inline-flex items-center gap-1.5">
            <BookOpenCheckIcon className="size-3.5" />
            {steps.length === 1 ? "1 paso" : `${steps.length} pasos`}
            {total === null ? "" : ` · ${duration(total)}`}
          </span>
        )}
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        {steps.map((step) => (
          <ChainOfThoughtStep
            description={step.elapsed_s === null ? undefined : duration(step.elapsed_s)}
            icon={ICONS[step.id]}
            key={step.id}
            label={step.label}
            status={step.status === "running" ? "active" : "complete"}
          />
        ))}
      </ChainOfThoughtContent>
    </ChainOfThought>
  )
}
