"use client"

import { memo, type CSSProperties, type ElementType } from "react"

import { cn } from "@/lib/utils"

export interface TextShimmerProps {
  children: string
  as?: ElementType
  className?: string
  duration?: number
  spread?: number
}

/** Moving highlight over muted text. CSS only: it keeps running while the main thread is busy. */
function ShimmerComponent({
  children,
  as: Component = "span",
  className,
  duration = 2,
  spread = 2,
}: TextShimmerProps) {
  const style = {
    "--shimmer-spread": `${(children?.length ?? 0) * spread}px`,
    "--shimmer-duration": `${duration}s`,
  } as CSSProperties
  return (
    <Component
      className={cn("text-shimmer inline-block", className)}
      style={style}
    >
      {children}
    </Component>
  )
}

export const Shimmer = memo(ShimmerComponent)
