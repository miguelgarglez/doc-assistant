"use client"

import { ChevronDownIcon, FileTextIcon } from "lucide-react"
import type { ComponentProps } from "react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

export const Sources = ({
  className,
  ...props
}: ComponentProps<typeof Collapsible>) => (
  <Collapsible className={cn("text-sm", className)} {...props} />
)

export const SourcesTrigger = ({
  className,
  count,
  children,
  ...props
}: ComponentProps<typeof CollapsibleTrigger> & { count: number }) => (
  <CollapsibleTrigger
    className={cn(
      "group flex items-center gap-1.5 rounded-md py-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
      className
    )}
    {...props}
  >
    {children ?? (
      <>
        {count === 1 ? "1 fuente" : `${count} fuentes`}
        <ChevronDownIcon className="size-3.5 transition-transform duration-200 group-data-[panel-open]:rotate-180" />
      </>
    )}
  </CollapsibleTrigger>
)

export const SourcesContent = ({
  className,
  ...props
}: ComponentProps<typeof CollapsibleContent>) => (
  <CollapsibleContent className={cn("flex flex-col", className)} {...props} />
)

export const Source = ({
  className,
  children,
  ...props
}: ComponentProps<"button">) => (
  <button
    className={cn(
      "flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
      className
    )}
    type="button"
    {...props}
  >
    {children ?? <FileTextIcon className="mt-0.5 size-4 shrink-0" />}
  </button>
)
