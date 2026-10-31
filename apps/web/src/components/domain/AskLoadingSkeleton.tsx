import { Skeleton } from "@/components/ui/skeleton"

export function AskLoadingSkeleton() {
  return (
    <section
      className="grid gap-6 lg:grid-cols-2"
      aria-busy="true"
      aria-live="polite"
      aria-label="Consultando documentación"
      data-testid="ask-loading"
    >
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-4 w-3/4" />
        <div className="flex flex-col gap-2 pt-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-7 w-36" />
          <Skeleton className="h-7 w-28" />
        </div>
      </div>
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="aspect-[3/4] w-full max-h-72" />
        <Skeleton className="h-16 w-full" />
      </div>
    </section>
  )
}
