"use client"

import type { ComponentProps, HTMLAttributes } from "react"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

/** AI Elements "artifact" on Base UI: a bordered container with a header, actions and a body. */
export const Artifact = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex w-full min-w-0 flex-col overflow-hidden rounded-xl border bg-card text-card-foreground", className)} {...props} />
)

export const ArtifactHeader = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex min-h-11 items-center justify-between gap-3 border-b bg-muted/40 px-4 py-2", className)} {...props} />
)

export const ArtifactTitle = ({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("font-heading text-sm font-semibold text-foreground", className)} {...props} />
)

export const ArtifactDescription = ({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("text-xs text-muted-foreground", className)} {...props} />
)

export const ArtifactActions = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex items-center gap-1", className)} {...props} />
)

export type ArtifactActionProps = ComponentProps<typeof Button> & { label: string }

/** Icon action with a tooltip. The accessible name is `label`. */
export const ArtifactAction = ({ label, children, className, size = "icon-sm", variant = "ghost", ...props }: ArtifactActionProps) => (
  <Tooltip>
    <TooltipTrigger
      render={
        <Button
          aria-label={label}
          className={cn("text-muted-foreground hover:text-foreground", className)}
          size={size}
          type="button"
          variant={variant}
          {...props}
        />
      }
    >
      {children}
    </TooltipTrigger>
    <TooltipContent>{label}</TooltipContent>
  </Tooltip>
)

export const ArtifactContent = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("min-w-0 flex-1 p-4", className)} {...props} />
)
