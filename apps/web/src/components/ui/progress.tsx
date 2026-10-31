import { cn } from "@/lib/utils"

type ProgressProps = {
  value: number
  className?: string
  label?: string
  "data-testid"?: string
}

export function Progress({
  value,
  className,
  label,
  "data-testid": testId = "progress",
}: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className={cn("flex w-full flex-col gap-1.5", className)} data-testid={testId}>
      {label ? (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>{label}</span>
          <span className="tabular-nums">{clamped}%</span>
        </div>
      ) : null}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-label={label ?? "Progreso"}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-[var(--duration-ui)] ease-[var(--ease-out)] motion-reduce:transition-none"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}
