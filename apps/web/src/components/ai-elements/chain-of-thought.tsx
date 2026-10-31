"use client"

import type { LucideIcon } from "lucide-react"
import { ChevronDownIcon, DotIcon } from "lucide-react"
import type { ComponentProps, ReactNode } from "react"
import { createContext, memo, useContext, useMemo } from "react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { useControllableState } from "@/lib/use-controllable-state"
import { cn } from "@/lib/utils"

type ChainOfThoughtContextValue = {
  isOpen: boolean
  setIsOpen: (open: boolean) => void
}

const ChainOfThoughtContext = createContext<ChainOfThoughtContextValue | null>(null)

const useChainOfThought = () => {
  const context = useContext(ChainOfThoughtContext)
  if (!context) throw new Error("ChainOfThought components need a ChainOfThought parent")
  return context
}

export type ChainOfThoughtProps = Omit<ComponentProps<"div">, "onChange"> & {
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
}

/** Collapsible list of pipeline steps. Header and body share one open state. */
export const ChainOfThought = memo(
  ({ className, open, defaultOpen = false, onOpenChange, children, ...props }: ChainOfThoughtProps) => {
    const [isOpen, setIsOpen] = useControllableState({
      defaultProp: defaultOpen,
      onChange: onOpenChange,
      prop: open,
    })
    const value = useMemo(() => ({ isOpen, setIsOpen }), [isOpen, setIsOpen])
    return (
      <ChainOfThoughtContext.Provider value={value}>
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <div className={cn("w-full", className)} {...props}>
            {children}
          </div>
        </Collapsible>
      </ChainOfThoughtContext.Provider>
    )
  }
)

export const ChainOfThoughtHeader = memo(
  ({ className, children, ...props }: ComponentProps<typeof CollapsibleTrigger>) => {
    const { isOpen } = useChainOfThought()
    return (
      <CollapsibleTrigger
        className={cn(
          "flex w-fit max-w-full items-center gap-1.5 rounded-md py-1 text-left text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
          className
        )}
        {...props}
      >
        <span className="min-w-0 truncate">{children}</span>
        <ChevronDownIcon
          className={cn(
            "size-4 shrink-0 transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </CollapsibleTrigger>
    )
  }
)

export type ChainOfThoughtStepProps = ComponentProps<"li"> & {
  icon?: LucideIcon
  label: ReactNode
  description?: ReactNode
  status?: "complete" | "active" | "pending"
}

const stepStatusStyles = {
  active: "text-foreground",
  complete: "text-muted-foreground",
  pending: "text-muted-foreground/60",
}

export const ChainOfThoughtStep = memo(
  ({ className, icon: Icon = DotIcon, label, description, status = "complete", children, ...props }: ChainOfThoughtStepProps) => (
    <li
      className={cn("relative flex gap-2.5 pb-3 text-sm last:pb-0", stepStatusStyles[status], className)}
      data-status={status}
      {...props}
    >
      <div className="relative mt-0.5 flex size-4 shrink-0 items-center justify-center">
        <Icon className="size-4" />
        <div className="absolute top-5 -bottom-3 left-1/2 w-px -translate-x-1/2 bg-border in-[li:last-child]:hidden" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="leading-5">{label}</div>
        {description ? <div className="text-xs text-muted-foreground">{description}</div> : null}
        {children}
      </div>
    </li>
  )
)

export const ChainOfThoughtContent = memo(
  ({ className, children, ...props }: ComponentProps<typeof CollapsibleContent>) => (
    <CollapsibleContent className={cn(className)} {...props}>
      <ol className="mt-2 flex flex-col border-l border-transparent pl-0.5">{children}</ol>
    </CollapsibleContent>
  )
)

ChainOfThought.displayName = "ChainOfThought"
ChainOfThoughtHeader.displayName = "ChainOfThoughtHeader"
ChainOfThoughtStep.displayName = "ChainOfThoughtStep"
ChainOfThoughtContent.displayName = "ChainOfThoughtContent"
